# Required behavior of `executable`

The artifact is a single runnable program named exactly `executable`. It is a
command-line LaTeX source formatter compatible with the behavior below. Unless
stated otherwise, text is UTF-8, output line endings are `\n`, successful
commands return status 0, normal formatted output goes to stdout, diagnostics go
to stderr, and every formatted document ends in exactly one newline.

## Spec 1

The command-line grammar is:

```text
executable [OPTIONS] [files]...
```

It accepts these options and aliases. Boolean short options may be combined
(for example, `-vp`). Options taking a value accept both a separate value and
the usual equals forms (`--wraplen=40` and `-l=40`).

| Option | Meaning |
|---|---|
| `-c`, `--check` | Check formatting without writing files. |
| `-p`, `--print` | Format file input to stdout without writing files. |
| `-f`, `--fail-on-change` | Write formatted files, but return 1 if any file changed. |
| `-n`, `--nowrap` | Disable line wrapping only; other formatting still occurs. |
| `-l N`, `--wraplen N` | Set the wrapping length. Default 80. |
| `-t N`, `--tabsize N` | Set indentation width. Default 2. |
| `--usetabs` | Use tab characters rather than spaces for each indentation unit. |
| `-s`, `--stdin` | Read one document from stdin and write it to stdout. |
| `--config PATH` | Select a TOML configuration file. |
| `--noconfig` | Disable all configuration-file loading. |
| `-v`, `--verbose` | Enable informational messages. |
| `-q`, `--quiet` | Suppress warnings. |
| `--trace` | Enable trace and informational messages. |
| `--completion SHELL` | Emit a completion script for a supported shell. |
| `--man` | Emit a roff manual page. |
| `--args` | Emit the resolved arguments and exit without processing input. |
| `-r`, `--recursive` | Recursively discover supported files. |
| `-h`, `--help` | Show help. |
| `-V`, `--version` | Show the version. |

`wraplen` is a nonnegative integer with no 8-bit ceiling: 0 and 1000 are both
accepted, while a negative value or non-integer is an argument error. `tabsize`
is parsed as an unsigned 8-bit integer, so non-integers and values above 255 are
argument errors. `--completion` accepts exactly `bash`, `elvish`, `fish`,
`powershell`, and `zsh`.

## Spec 2

`--version` must write exactly `tex-fmt 0.5.6\n` to stdout, write nothing to
stderr, and return 0. `-V` also returns 0 and prints a single line beginning
with `tex-fmt`.

`--help` must write exactly the following, including the final newline, to
stdout, write nothing to stderr, and return 0. Help handling is order-sensitive:
an earlier syntax error prevents a later help option from taking effect. In
particular, `--unknown --help` returns 2, writes no stdout, and reports the
unexpected `--unknown` argument on stderr. By contrast, `-h` returns 0, and
`--help -- --bad` returns 0 with the normal help on stdout and no stderr.

```text
tex-fmt 0.5.6

LaTeX formatter written in Rust

Usage: executable [OPTIONS] [files]...

Arguments:
  [files]...  List of files to be formatted

Options:
  -c, --check               Check formatting, do not modify files
  -p, --print               Print to stdout, do not modify files
  -f, --fail-on-change      Format files and return non-zero exit code if files are modified
  -n, --nowrap              Do not wrap long lines
  -l, --wraplen <N>         Line length for wrapping [default: 80]
  -t, --tabsize <N>         Number of characters to use as tab size [default: 2]
      --usetabs             Use tabs instead of spaces for indentation
  -s, --stdin               Process stdin as a single file, output to stdout
      --config <PATH>       Path to config file
      --noconfig            Do not read any config file
  -v, --verbose             Show info messages
  -q, --quiet               Hide warning messages
      --trace               Show trace messages
      --completion <SHELL>  Generate shell completion script [possible values: bash, elvish, fish, powershell, zsh]
      --man                 Generate man page
      --args                Print arguments passed to tex-fmt and exit
  -r, --recursive           Recursively search for files to format
  -h, --help                Print help
  -V, --version             Print version
```

The short help option must at least provide this same help interface (including
`Usage:`) and return 0.

## Spec 3

Command-line syntax errors return 2 and are written to stderr in clap-style
wording. Unknown options include `error: unexpected argument '<option>' found`,
the usage `Usage: executable [OPTIONS] [files]...`, and
`For more information, try '--help'.`. They also suggest the `--` separator.
For example, `--unknown-flag` produces exactly:

```text
error: unexpected argument '--unknown-flag' found

  tip: to pass '--unknown-flag' as a value, use '-- --unknown-flag'

Usage: executable [OPTIONS] [files]...

For more information, try '--help'.
```

A missing option value says `a value is required` and names the option. An
invalid completion shell says `invalid value`, names `--completion`, and lists
possible values. Invalid numeric text includes wording such as
`invalid value 'abc'`. In particular, `--tabsize 999` writes exactly:

```text
error: invalid value '999' for '--tabsize <N>': 999 is not in 0..=255

For more information, try '--help'.
```

The token `--` terminates option parsing. Later flag-looking tokens are file
names, not options; failure to open one is consequently an operational error
(status 1), not an argument error.

## Spec 4

After configuration and command-line merging, `--args` prints the resolved
state and immediately returns 0, without requiring files to exist or formatting
them. It writes no diagnostic. Labels begin with two spaces and are padded so
values begin in column 27; further values of list fields align with the first.
The fields, in order, are `check`, `print`, `fail-on-change`, `wrap`, `wraplen`,
`wrapmin`, `tabsize`, `tabchar`, `stdin`, `config`, `verbosity`, `lists`,
`verbatims`, `no-indent-envs`, `wrap-chars`, and `files`. Empty lists are
omitted. When there is no selected path, `config` is displayed as `None`;
tab choice is `space` or `tab`. `--noconfig` prevents configuration contents
from being read, but it does not clear a simultaneously supplied explicit
path from this display: `--args --config PATH --noconfig` reports `PATH` in
the `config` field while applying defaults.

The built-in lists are `itemize`, `enumerate`, `description`, `inlineroman`,
and `inventory`; built-in verbatim environments are `verbatim`, `Verbatim`,
`lstlisting`, `minted`, and `comment`; the built-in no-indent environment is
`document`; and the built-in wrap character is a single space. Default
verbosity is `warn`. `wrapmin` defaults to `wraplen - 10` when wraplen is at
least 50 and otherwise to wraplen.

For example, in a working directory where `/workspace/tex-fmt.toml` is the
discovered config, this command:

```sh
./executable --args --check --nowrap --tabsize 4 test.tex
```

prints exactly:

```text
tex-fmt
  check:                   true
  print:                   false
  fail-on-change:          false
  wrap:                    false
  wraplen:                 80
  wrapmin:                 70
  tabsize:                 4
  tabchar:                 space
  stdin:                   false
  config:                  /workspace/tex-fmt.toml
  verbosity:               warn
  lists:                   itemize
                           enumerate
                           description
                           inlineroman
                           inventory
  verbatims:               verbatim
                           Verbatim
                           lstlisting
                           minted
                           comment
  no-indent-envs:          document
  wrap-chars:               
  files:                   test.tex
```

For compatibility, the displayed `fail-on-change` value follows the resolved
`print` value: `--print --args` reports both as true, while `--check --args`
reports `fail-on-change: false`. `--stdin` implies print mode. `--usetabs`
reports `tabchar: tab`. Verbosity resolution is priority-based, independent of
argument order: trace beats verbose, verbose beats quiet, and these display as
`trace`, `info`, and `error` respectively.

## Spec 5

With ordinary file arguments and no mode option, each file is formatted and
overwritten in place. This successful mode is silent unless a warning is
needed. Multiple files are all processed.

`--print` formats every named file, concatenates their formatted texts on
stdout, and never changes the files. `--stdin` similarly formats all stdin as
one logical file named `<stdin>`, implies print behavior, and accepts no file
arguments. Supplying both stdin mode and file names returns 1 and includes
`ERROR: tex-fmt : Do not provide file name(s) when using --stdin.` on stderr.

`--check` is read-only. For each file whose bytes differ from formatted output,
it emits `ERROR: tex-fmt PATH: Incorrect formatting. ` followed by a newline.
The aggregate status is 1 if at least one file is incorrect, otherwise 0.

`--fail-on-change` is not read-only: it writes the formatted result. It returns
1 if at least one file was modified and 0 when no file changed. It is silent at
default verbosity.

An unreadable/nonexistent input returns 1, does not create it, writes no stdout,
and reports `ERROR: tex-fmt PATH: Could not open file. ` followed by a newline,
where `PATH` is the name after the extension inference in Spec 6.
Other valid inputs continue to be considered in a multiple-file invocation.
No inputs outside `--stdin`/recursive discovery returns 1 with:

```text
ERROR: tex-fmt : No files specified. Provide filenames, or pass --recursive or --stdin. 
```

Passing a directory without recursive mode returns 1 and includes
`ERROR: tex-fmt : A directory was passed without --recursive.`.

## Spec 6

Explicitly named files are processed as UTF-8 LaTeX-family source. Before a
non-directory argument with no extension is opened, `.tex` is appended to it.
This also applies to a flag-looking file name after `--`: in an empty directory,
`--noconfig -- --unknown-flag` returns 1 and writes exactly
`ERROR: tex-fmt --unknown-flag.tex: Could not open file. \n` to stderr. The
supported extensions for discovery are `.tex`, `.bib`, `.sty`, and `.cls`; all
use the same structural formatter. Symlinked files are followed.

With `--recursive`, each directory argument is walked recursively. With no
directory argument, `./` is searched. Files of the four extensions are
collected; other extensions, hidden directories, and files excluded by
`.gitignore` or `.ignore` rules are skipped. For the required ignore syntax,
nonblank lines name paths relative to the ignore file; `/` separates path
components, a trailing `/` excludes that directory and everything below it,
and `*` matches arbitrary non-separator characters (so `ignored/`,
`sub/a.tex`, and `*.bak.tex` have their usual literal meanings). Ignore files
in relevant parent directories apply; `.gitignore` applies when walking a Git
repository. Symlinked directory traversal must not loop. Multiple directory
arguments work and deeply nested files are found. Results are not deduplicated
across overlapping directory arguments: each argument is walked separately in
argument order, so a file found through more than one argument is processed
more than once. For example, if `root/one/a.tex` contains `A` and
`root/two/b.tex` contains `B`, then
`--recursive --print root root/one root/two` writes exactly
`A\nB\nA\nB\n`. Default mode writes discovered files;
print/check/fail-on-change retain their normal meanings. If discovery yields no
files, use the no-files error from Spec 5.

## Spec 7

Configuration uses the needed subset of TOML: `name = value` assignments,
decimal integers, `true`/`false`, double-quoted strings, arrays in brackets,
whitespace, blank lines, and `#` comments. Unless `--noconfig` is present, choose exactly one
config in this priority order: the explicit `--config PATH`; `tex-fmt.toml` in
the current working directory; then `tex-fmt.toml` at the root of the enclosing
Git repository. Relative explicit paths are relative to the working directory.
`--noconfig` disables loading and parsing even a simultaneously supplied
explicit path. As specified in Spec 4, that explicit path is nevertheless
retained in `--args` output.

Supported tested keys and types are:

| Key | Type/effect |
|---|---|
| `print`, `fail-on-change`, `wrap` | Boolean mode values. |
| `wraplen`, `wrapmin` | Nonnegative integer values. |
| `tabsize` | An unsigned 8-bit integer value. |
| `tabchar` | `"space"` or `"tab"`. |
| `lists` | Array of additional list-environment names. |
| `verbatims` | Array of additional verbatim-environment names. |
| `no-indent-envs` | Array of additional non-indenting environment names. |
| `wrap-chars` | Array of one-character strings usable as wrap points. |
| `verbosity` | `"verbose"` or `"info"` enables informational logging. |

Arrays extend the built-ins rather than replacing them. Configured entries are
placed before the built-ins, then consecutive equal entries are collapsed;
equal values separated by another entry remain duplicated. For example,
`lists = ["itemize", "tasks"]` resolves to `itemize`, `tasks`, `itemize`,
`enumerate`, `description`, `inlineroman`, `inventory`; and
`verbatims = ["minted", "raw"]` resolves to `minted`, `raw`, `verbatim`,
`Verbatim`, `lstlisting`, `minted`, `comment`. Likewise,
`no-indent-envs = ["document", "outer"]` resolves to `document`, `outer`,
`document`, while `wrap-chars = ["-", "-"]` resolves to `-` followed by the
built-in space because the two adjacent hyphens collapse. Unknown keys are
ignored. An empty file applies defaults. Explicit CLI formatting values
override matching config values, while config still supplies formatting fields
absent on the CLI. Thus a config containing `wraplen = 40` is overridden by
`--wraplen 80`; CLI tabsize and `--usetabs` override configured tabsize/tabchar;
and `--nowrap` overrides `wrap = true`.

A missing explicit config or malformed TOML terminates nonzero. Malformed TOML
must include `Failed to read config file`, `panicked at src/config.rs`, and its
path in stderr. A missing path includes `panicked at src/config.rs` and
`No such file or directory`. A known key of the wrong type terminates nonzero;
the tested type failure includes `panicked at src/config.rs` and
``called `Option::unwrap()` on a `None` value``.

## Spec 8

Before line-by-line structural formatting, normalize the document as follows.
The order of the first two operations is significant:

1. In the raw input, collapse any run of three or more consecutive LF (`\n`)
   bytes to exactly two. A CR byte between LF bytes prevents them from being
   consecutive for this operation.
2. Convert the remaining CRLF/mixed input into normal logical lines and emit LF
   output. Because this happens after step 1, a run of CRLF sequences is not
   collapsed. In particular, the input
   `one  \r\n\r\n\r\ntwo\r\nthree\n\n\n\n` formats to exactly
   `one\n\n\ntwo\nthree\n` after the remaining cleanup steps.
3. In space-indentation mode, replace every input tab everywhere—including in
   a verbatim block—with `tabsize` spaces. In tab-indentation mode, preserve
   existing tabs.
4. Remove spaces immediately before newline. A whitespace-only logical line
   becomes empty.
5. At completion, trim all trailing whitespace/blank lines and append exactly
   one newline. Even an empty input therefore formats to `"\n"`.

Internal runs of spaces in nonblank content are otherwise preserved. Unicode
must be preserved byte-for-byte at character boundaries, and line-length logic
counts Unicode scalar characters rather than UTF-8 bytes. Formatting is
idempotent: formatting already formatted output produces exactly itself.

For each cleaned logical line, use this order: determine whether ignore or
verbatim protection applies; if not protected, perform one structural split and
requeue both pieces for the same procedure until no split remains; compute the
piece's indentation; if it needs wrapping, split and requeue both pieces for the
same procedure; finally apply leading indentation and emit it. Process prefixes
before suffixes. A requeued piece keeps the original source-line number but gets
its own generated-line number.

## Spec 9

Before indenting and wrapping, place structural commands on new logical lines
when they have non-whitespace content before them. The recognized starts are
`\begin{...}`, `\end{...}`, `\item` (only when not followed by an ASCII
letter), `\section{...}`, `\subsection{...}`, `\subsubsection{...}` and starred
forms, plus `\chapter{...}`/`\chapter*{...}` and
`\part{...}`/`\part*{...}`. Apply repeatedly so multiple constructs on one
source line are separated in order. Do not force text following a construct
onto another line merely because it follows that construct.

For example:

```text
Text \section{S} more \subsection*{T} and more
```

becomes:

```text
Text
\section{S} more
\subsection*{T} and more
```

Likewise, `\item\item Adjacent` becomes two adjacent item lines, and
`\item First \end{itemize}` places the end marker on the next line. A marker
after the first genuine, unescaped `%` comment delimiter does not cause a split.
An escaped `\%` is not a comment delimiter, so a later structural command still
splits. A source line containing `\verb` or `\mintinline` is a whole-line
exception: no structural split is performed anywhere on that line, including
at commands after the inline literal has ended. Consequently these two lines
remain exactly these two lines under `--nowrap`:

```tex
before \verb|\section{No} \item| after \section{Yes}
x \mintinline{tex}{\end{x}} y \part*{P}
```

## Spec 10

Indentation is stateful and starts at logical level zero. Strip existing leading
whitespace from each non-ignored line and prefix its computed visual level using
`tabsize` copies of the selected indent character. With spaces, level 1 is two
spaces by default. With `--usetabs`, each one of those `tabsize` copies is a
literal tab, so default level 1 is two tabs (tabsize remains a count of indent
characters, not a visual tab stop).

Every `\begin{name}` except a configured no-indent environment increases the
following actual level by one; its matching `\end{name}` decreases by one and
is visually placed at the outer level. `document` is non-indenting by default.
Environment names need not be from a fixed list: figure, equation, align,
theorem, proof, abstract, minipage, center, quote, tabular, and other ordinary
environments all use this rule. Optional/required arguments after a begin do not
change it.

Built-in or configured list environments increase the actual level by two.
Their `\item` lines visually back up one level; item continuation lines remain
at the full two-level depth. The list end backs up two levels. This composes for
nested lists. The item-line backup has the inline-literal exception described in
Spec 14: if an item line contains `\verb` or `\mintinline`,
environment/list/item analysis is disabled and it stays at the current actual
level. Delimiter nesting is still counted as specified in Specs 11 and 14. Thus:

```tex
\begin{itemize}
\item Outer
continuation
\begin{enumerate}
\item Inner
\end{enumerate}
\end{itemize}
```

formats with default settings as:

```tex
\begin{itemize}
  \item Outer
    continuation
    \begin{enumerate}
      \item Inner
    \end{enumerate}
\end{itemize}
```

An orphan `\item` at level zero remains at level zero. Comment-only lines use
the current actual level, not the visual one-level backup used by an item.

## Spec 11

Delimiter nesting also contributes indentation. Count every `{`, `(`, and
`[` as opens and `}`, `)`, and `]` as closes, without requiring matching types.
On a line, leading/excess closes visually dedent that line; the net open-minus-
close count changes the actual level for following lines. Balanced delimiters
on one line have no lasting effect. Ignore characters after a genuine comment
delimiter. An inline verb construct is not exempt from delimiter counting:
delimiters inside the literal payload are counted and change the actual level
for following lines. Thus this input under `--nowrap`:

```tex
before % {{{
next
\verb|{{{|
last
```

becomes exactly:

```tex
before % {{{
next
\verb|{{{|
      last
```

Examples with default indentation:

```tex
\command{
  \option[
    \paren(
      content
    )
  ]
}
```

and three opens on `\command{{{` indent the next line by six spaces. Delimiter
indent combines additively with environment/list indentation. Negative computed
levels are clamped to zero for output and reported as described in Spec 17;
formatting malformed LaTeX still completes with status 0 unless another mode or
I/O condition changes the status.

## Spec 12

Wrapping is enabled by default. A line needs wrapping when its Unicode-character
count plus its computed indentation is strictly greater than `wraplen`. `nowrap`
disables this phase but not indentation, splitting, cleanup, or other formatting.

`wrapmin` is the target breakpoint: if absent it is `wraplen - 10` for wraplen
at least 50, otherwise exactly wraplen; an explicit value is capped at wraplen.
For each overlong segment, scan from the beginning and retain eligible wrap
characters. Choose the last eligible point strictly before
`wrapmin - indentation`; if none exists before that boundary, choose the first
eligible point after it. Keep the chosen separator at the end of the prefix
(the later trailing-space cleanup removes it when it is the normal space
separator), put the suffix into the formatting queue, and repeat until no split
can be made. This
behavior intentionally produces balanced lines around the target rather than
always filling to `wraplen`.

The default eligible character is space. Configured `wrap-chars` add characters
such as `-`. A candidate preceded immediately by backslash is ineligible; a
candidate at end of line is ineligible; candidates inside inline verb content
are ineligible. If no point exists, emit a `Line cannot be wrapped.` warning and
preserve the overlong line. A selected point is also considered late, and emits
the warning, when its zero-based UTF-8 byte offset is greater than `wraplen`;
this warning check uses the byte offset even though the need-to-wrap and target
calculations use Unicode-character counts. A late point is still split and
processing continues, which lets an indivisible URL or verb construct occupy
its own overlong line. Preserve all content and internal repeated spaces.
Wrapped continuations are reprocessed for indentation, so open/closing
delimiters can alter continuation indentation.

For example, formatting stdin `Café こんにちは 世界 😀😀` with `--wraplen 14`
returns 0 and writes:

```text
Café こんにちは 世界
😀😀
```

It also writes this line-specific warning, with no space after the final emoji:

```text
WARN: tex-fmt <stdin>: Line 1 (1). Line cannot be wrapped. Café こんにちは 世界 😀😀
```

Representative exact results are:

```text
# wraplen 80
This is a very long line that definitely exceeds the default 80
character wrap length and should be wrapped at a space boundary.

# wraplen 40
This is a very long line that
definitely exceeds the default 80
character wrap length and should be
wrapped at a space boundary.

# input "a b c d", wraplen 5
a b
c d
```

At a length limit, a line equal to the limit is not wrapped. A short line and a
single long word are not altered (the latter warns). Continuation indentation is
included in the threshold.

## Spec 13

The first `%` not immediately preceded by `\` starts a LaTeX comment, except a
percent inside a recognized inline verb construct. Preserve the marker and all
comment content, including multiple markers (`%%`, `%%%`), braces, commands,
math, and Unicode. `\%` remains ordinary text; in `\%\% ... % comment`, only
the last unescaped percent starts the comment. A backslash followed by a space
does not escape a later percent.

Comment-only lines receive normal current indentation. For example comments in
an itemize body, between items, are indented four spaces by default, while item
lines use two. Existing arbitrary spaces/tabs before comments are normalized.
Consecutive comment lines and blank lines between them remain separate.

Normal wrapping applies to comments. If a wrap point is after the comment
delimiter, every continuation is prefixed with `% ` at the continuation's
computed indentation. This applies to both full-line and inline comments:

```text
% This is a very long comment line that definitely exceeds the
% default 80 character wrap length and should be wrapped at a space boundary.
```

```text
This is text before the comment % This is a very long comment that
% exceeds the default 80 character wrap length and should be wrapped
% with percent continuation.
```

`--nowrap` preserves a long comment on one line. A long comment without any
eligible separator is preserved and warns.

## Spec 14

Inline literal constructs protect their contents from wrapping when their line
is handled successfully. Recognize `\verb` with its following delimiter
(including `|` and `+`) through the matching delimiter, and recognize
`\mintinline` including its language and braced literal body. Percent signs and
structural commands inside them are literal. A long line containing `\verb` may
wrap before and after the entire construct, but never within it. Warn if the
resulting atomic line is strictly over `wraplen`; wrapping on both sides alone
does not cause a warning. For example, the middle line below has 79 characters,
so at the default `wraplen` the transformation is silent:

```text
This line contains a
\verb+very long verbatim section with plus delimiters that should not be split+
end.
```

An over-limit line containing `\mintinline` instead fails when wrapping is
entered. In particular, formatting the no-final-newline stdin text
`before \mintinline{tex}{a b % \section{x}} after words here` with
`--noconfig --quiet --stdin --wraplen 30` writes no stdout, returns status 101,
and writes a panic to stderr containing, in order,
`panicked at src/wrap.rs:<error location>`,
``called `Option::unwrap()` on a `None` value``, and
`RUST_BACKTRACE=1`. The same text with `--nowrap` or `--wraplen 80` returns 0
and writes the original text followed by one newline.

The presence of either construct also disables structural splitting and the
environment/list/item parts of indentation analysis for the entire source line,
not only for the literal's contents. The line therefore does not visually back
up for an item or end marker and is emitted at the current actual indentation
level. It does not disable the delimiter nesting rule in Spec 11: braces and
other delimiters anywhere on the line, including in the literal payload, still
change the actual indentation of following lines. For example, in an `itemize`
at default settings, `\item Normal` has two leading spaces but
`\item With \verb|{code}| inline` has four.

## Spec 15

The default verbatim environments are `verbatim`, `Verbatim`, `lstlisting`,
`minted`, and `comment`; config may add names. From a recognized begin line
through its recognized end line inclusive, do not split, wrap, trim/reindent the
line, or interpret LaTeX/comments. The whole-file preprocessing in Spec 8 still
applies, notably default tab-to-space conversion and global newline/trailing-
space cleanup.

Track verbatim depth with one counter shared by all recognized types, so nested
begins work and begin/end types need not match. An unclosed begin simply protects
the rest of the file. An end that drives the counter negative warns on that and
subsequent negative-depth lines; it does not abort.

Separately, a line ending exactly in `% tex-fmt: skip` is exempt from line-level
formatting. A line ending `% tex-fmt: off` begins a Boolean ignored block, and a
line ending `% tex-fmt: on` ends it; both directive lines and all lines while off
are exempt. Directives must be suffixes and are preserved. Beginning an already
active block warns `Cannot begin ignore block:`; ending an inactive block warns
`No ignore block to end.`. Global preprocessing still precedes ignore handling.

## Spec 16

These canonical format examples are normative. Default formatting changes:

```tex
\documentclass{article}
\begin{document}
\section{Introduction}
This is some text that is quite long and should be wrapped to multiple lines when formatting is applied with default settings of 80 characters per line.
\begin{itemize}
\item First item with some text
\item Second item
\item Third item that is also quite long and might need wrapping depending on the configuration
\end{itemize}
\subsection{Mathematics}
Here is an equation:
\begin{equation}
f(x)=\int_{0}^{\infty}e^{-x^2}dx
\end{equation}
\end{document}
```

into exactly:

```tex
\documentclass{article}
\begin{document}
\section{Introduction}
This is some text that is quite long and should be wrapped to
multiple lines when formatting is applied with default settings of 80
characters per line.
\begin{itemize}
  \item First item with some text
  \item Second item
  \item Third item that is also quite long and might need wrapping
    depending on the configuration
\end{itemize}
\subsection{Mathematics}
Here is an equation:
\begin{equation}
  f(x)=\int_{0}^{\infty}e^{-x^2}dx
\end{equation}
\end{document}
```

With `--nowrap`, only the indentation/cleanup changes and both long prose/item
lines remain intact. With `--tabsize 4`, every shown two-space indentation unit
becomes four spaces, including eight spaces on the wrapped continuation of the
long list item. Unicode examples such as `Café`, `こんにちは 世界`, Cyrillic,
CJK text, and emoji are preserved while receiving the same structural indent.

## Spec 17

Default verbosity is warnings. `--quiet` selects errors only; `--verbose`
selects info (and warnings/errors); `--trace` selects trace, info, warnings, and
errors. If combined, priority is trace, then verbose, then quiet, regardless of
order. Logs go to stderr after processing and have this shape:

```text
LEVEL: tex-fmt FILE: MESSAGE LINE-CONTENT
```

The formatter places one separator space between `MESSAGE` and the line-content
field. For a file-level record the field is empty, so that separator is the
trailing space before the newline, as in the lifecycle and byte-count examples
below. For a line-level record it is followed by the line content and no
additional trailing space is appended. Thus the trace example below ends
immediately after `\documentclass{article}`. Likewise, a negative-verbatim-depth
record for `\end{verbatim}` ends immediately after `\end{verbatim}`, and the
corresponding `\end{lstlisting}` record ends immediately after
`\end{lstlisting}`. A line-specific record can still end in a space when that
space belongs to its recorded pre-cleanup line content, as in the two exact wrap
warnings later in this section.

File lifecycle messages in verbose mode are:

```text
INFO: tex-fmt FILE: Formatting started. 
INFO: tex-fmt FILE: Formatting complete. 
```

Trace mode additionally logs stdin byte count and every formatted logical line,
for example:

```text
TRACE: tex-fmt <stdin>: Read 23 bytes. 
TRACE: tex-fmt FILE: Line 1 (1). Indent: actual = 0, visual = 0: \documentclass{article}
```

The first line number is the generated line number and the parenthesized number
is the original line number; split/wrapped lines share their original number.
Trace also reports `Placing environment on new line.` and `Wrapping long line.`
when applicable.

An unwrappable line warns:

```text
WARN: tex-fmt <stdin>: Line 1 (1). Line cannot be wrapped. <trimmed line>
```

For the no-newline stdin text `hello world this is a test` at wraplen 5,
stdout is exactly:

```text
hello
world
this
is a
test
```

and default-verbosity stderr is exactly:

```text
WARN: tex-fmt <stdin>: Line 1 (1). Line cannot be wrapped. hello 
WARN: tex-fmt <stdin>: Line 2 (1). Line cannot be wrapped. world 
```

Adding `--quiet` leaves the stdout unchanged and makes stderr empty.

A negative indent warns per affected line with `Indent is negative.` and is
clamped for output. At EOF, nonzero actual indentation warns
`Indent does not return to zero. Last non-indented line is line N`; after any
negative indent it also warns
`Negative indents. First negatively indented line is line N`. A verbatim depth
below zero warns `Verbatim count is negative.`. These warnings do not themselves
make formatting return nonzero, and quiet mode suppresses them.

## Spec 18

`--completion SHELL` returns 0, writes nothing to stderr, exits without reading
configuration or input, and writes the corresponding script below exactly.

For `bash`:

```bash
_tex-fmt() {
    local i cur prev opts cmd
    COMPREPLY=()
    if [[ "${BASH_VERSINFO[0]}" -ge 4 ]]; then
        cur="$2"
    else
        cur="${COMP_WORDS[COMP_CWORD]}"
    fi
    prev="$3"
    cmd=""
    opts=""

    for i in "${COMP_WORDS[@]:0:COMP_CWORD}"
    do
        case "${cmd},${i}" in
            ",$1")
                cmd="tex__fmt"
                ;;
            *)
                ;;
        esac
    done

    case "${cmd}" in
        tex__fmt)
            opts="-c -p -f -n -l -t -s -v -q -r -h -V --check --print --fail-on-change --nowrap --wraplen --tabsize --usetabs --stdin --config --noconfig --verbose --quiet --trace --completion --man --args --recursive --help --version [files]..."
            if [[ ${cur} == -* || ${COMP_CWORD} -eq 1 ]] ; then
                COMPREPLY=( $(compgen -W "${opts}" -- "${cur}") )
                return 0
            fi
            case "${prev}" in
                --wraplen)
                    COMPREPLY=($(compgen -f "${cur}"))
                    return 0
                    ;;
                -l)
                    COMPREPLY=($(compgen -f "${cur}"))
                    return 0
                    ;;
                --tabsize)
                    COMPREPLY=($(compgen -f "${cur}"))
                    return 0
                    ;;
                -t)
                    COMPREPLY=($(compgen -f "${cur}"))
                    return 0
                    ;;
                --config)
                    COMPREPLY=($(compgen -f "${cur}"))
                    return 0
                    ;;
                --completion)
                    COMPREPLY=($(compgen -W "bash elvish fish powershell zsh" -- "${cur}"))
                    return 0
                    ;;
                *)
                    COMPREPLY=()
                    ;;
            esac
            COMPREPLY=( $(compgen -W "${opts}" -- "${cur}") )
            return 0
            ;;
    esac
}

if [[ "${BASH_VERSINFO[0]}" -eq 4 && "${BASH_VERSINFO[1]}" -ge 4 || "${BASH_VERSINFO[0]}" -gt 4 ]]; then
    complete -F _tex-fmt -o nosort -o bashdefault -o default tex-fmt
else
    complete -F _tex-fmt -o bashdefault -o default tex-fmt
fi
```

For `elvish` (including its initial blank line):

```elvish

use builtin;
use str;

set edit:completion:arg-completer[tex-fmt] = {|@words|
    fn spaces {|n|
        builtin:repeat $n ' ' | str:join ''
    }
    fn cand {|text desc|
        edit:complex-candidate $text &display=$text' '(spaces (- 14 (wcswidth $text)))$desc
    }
    var command = 'tex-fmt'
    for word $words[1..-1] {
        if (str:has-prefix $word '-') {
            break
        }
        set command = $command';'$word
    }
    var completions = [
        &'tex-fmt'= {
            cand -l 'Line length for wrapping [default: 80]'
            cand --wraplen 'Line length for wrapping [default: 80]'
            cand -t 'Number of characters to use as tab size [default: 2]'
            cand --tabsize 'Number of characters to use as tab size [default: 2]'
            cand --config 'Path to config file'
            cand --completion 'Generate shell completion script'
            cand -c 'Check formatting, do not modify files'
            cand --check 'Check formatting, do not modify files'
            cand -p 'Print to stdout, do not modify files'
            cand --print 'Print to stdout, do not modify files'
            cand -f 'Format files and return non-zero exit code if files are modified'
            cand --fail-on-change 'Format files and return non-zero exit code if files are modified'
            cand -n 'Do not wrap long lines'
            cand --nowrap 'Do not wrap long lines'
            cand --usetabs 'Use tabs instead of spaces for indentation'
            cand -s 'Process stdin as a single file, output to stdout'
            cand --stdin 'Process stdin as a single file, output to stdout'
            cand --noconfig 'Do not read any config file'
            cand -v 'Show info messages'
            cand --verbose 'Show info messages'
            cand -q 'Hide warning messages'
            cand --quiet 'Hide warning messages'
            cand --trace 'Show trace messages'
            cand --man 'Generate man page'
            cand --args 'Print arguments passed to tex-fmt and exit'
            cand -r 'Recursively search for files to format'
            cand --recursive 'Recursively search for files to format'
            cand -h 'Print help'
            cand --help 'Print help'
            cand -V 'Print version'
            cand --version 'Print version'
        }
    ]
    $completions[$command]
}
```

For `fish`:

```fish
complete -c tex-fmt -s l -l wraplen -d 'Line length for wrapping [default: 80]' -r
complete -c tex-fmt -s t -l tabsize -d 'Number of characters to use as tab size [default: 2]' -r
complete -c tex-fmt -l config -d 'Path to config file' -r -F
complete -c tex-fmt -l completion -d 'Generate shell completion script' -r -f -a "bash\t''
elvish\t''
fish\t''
powershell\t''
zsh\t''"
complete -c tex-fmt -s c -l check -d 'Check formatting, do not modify files'
complete -c tex-fmt -s p -l print -d 'Print to stdout, do not modify files'
complete -c tex-fmt -s f -l fail-on-change -d 'Format files and return non-zero exit code if files are modified'
complete -c tex-fmt -s n -l nowrap -d 'Do not wrap long lines'
complete -c tex-fmt -l usetabs -d 'Use tabs instead of spaces for indentation'
complete -c tex-fmt -s s -l stdin -d 'Process stdin as a single file, output to stdout'
complete -c tex-fmt -l noconfig -d 'Do not read any config file'
complete -c tex-fmt -s v -l verbose -d 'Show info messages'
complete -c tex-fmt -s q -l quiet -d 'Hide warning messages'
complete -c tex-fmt -l trace -d 'Show trace messages'
complete -c tex-fmt -l man -d 'Generate man page'
complete -c tex-fmt -l args -d 'Print arguments passed to tex-fmt and exit'
complete -c tex-fmt -s r -l recursive -d 'Recursively search for files to format'
complete -c tex-fmt -s h -l help -d 'Print help'
complete -c tex-fmt -s V -l version -d 'Print version'
```

For `powershell` (including its initial blank line):

```powershell

using namespace System.Management.Automation
using namespace System.Management.Automation.Language

Register-ArgumentCompleter -Native -CommandName 'tex-fmt' -ScriptBlock {
    param($wordToComplete, $commandAst, $cursorPosition)

    $commandElements = $commandAst.CommandElements
    $command = @(
        'tex-fmt'
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
        'tex-fmt' {
            [CompletionResult]::new('-l', '-l', [CompletionResultType]::ParameterName, 'Line length for wrapping [default: 80]')
            [CompletionResult]::new('--wraplen', '--wraplen', [CompletionResultType]::ParameterName, 'Line length for wrapping [default: 80]')
            [CompletionResult]::new('-t', '-t', [CompletionResultType]::ParameterName, 'Number of characters to use as tab size [default: 2]')
            [CompletionResult]::new('--tabsize', '--tabsize', [CompletionResultType]::ParameterName, 'Number of characters to use as tab size [default: 2]')
            [CompletionResult]::new('--config', '--config', [CompletionResultType]::ParameterName, 'Path to config file')
            [CompletionResult]::new('--completion', '--completion', [CompletionResultType]::ParameterName, 'Generate shell completion script')
            [CompletionResult]::new('-c', '-c', [CompletionResultType]::ParameterName, 'Check formatting, do not modify files')
            [CompletionResult]::new('--check', '--check', [CompletionResultType]::ParameterName, 'Check formatting, do not modify files')
            [CompletionResult]::new('-p', '-p', [CompletionResultType]::ParameterName, 'Print to stdout, do not modify files')
            [CompletionResult]::new('--print', '--print', [CompletionResultType]::ParameterName, 'Print to stdout, do not modify files')
            [CompletionResult]::new('-f', '-f', [CompletionResultType]::ParameterName, 'Format files and return non-zero exit code if files are modified')
            [CompletionResult]::new('--fail-on-change', '--fail-on-change', [CompletionResultType]::ParameterName, 'Format files and return non-zero exit code if files are modified')
            [CompletionResult]::new('-n', '-n', [CompletionResultType]::ParameterName, 'Do not wrap long lines')
            [CompletionResult]::new('--nowrap', '--nowrap', [CompletionResultType]::ParameterName, 'Do not wrap long lines')
            [CompletionResult]::new('--usetabs', '--usetabs', [CompletionResultType]::ParameterName, 'Use tabs instead of spaces for indentation')
            [CompletionResult]::new('-s', '-s', [CompletionResultType]::ParameterName, 'Process stdin as a single file, output to stdout')
            [CompletionResult]::new('--stdin', '--stdin', [CompletionResultType]::ParameterName, 'Process stdin as a single file, output to stdout')
            [CompletionResult]::new('--noconfig', '--noconfig', [CompletionResultType]::ParameterName, 'Do not read any config file')
            [CompletionResult]::new('-v', '-v', [CompletionResultType]::ParameterName, 'Show info messages')
            [CompletionResult]::new('--verbose', '--verbose', [CompletionResultType]::ParameterName, 'Show info messages')
            [CompletionResult]::new('-q', '-q', [CompletionResultType]::ParameterName, 'Hide warning messages')
            [CompletionResult]::new('--quiet', '--quiet', [CompletionResultType]::ParameterName, 'Hide warning messages')
            [CompletionResult]::new('--trace', '--trace', [CompletionResultType]::ParameterName, 'Show trace messages')
            [CompletionResult]::new('--man', '--man', [CompletionResultType]::ParameterName, 'Generate man page')
            [CompletionResult]::new('--args', '--args', [CompletionResultType]::ParameterName, 'Print arguments passed to tex-fmt and exit')
            [CompletionResult]::new('-r', '-r', [CompletionResultType]::ParameterName, 'Recursively search for files to format')
            [CompletionResult]::new('--recursive', '--recursive', [CompletionResultType]::ParameterName, 'Recursively search for files to format')
            [CompletionResult]::new('-h', '-h', [CompletionResultType]::ParameterName, 'Print help')
            [CompletionResult]::new('--help', '--help', [CompletionResultType]::ParameterName, 'Print help')
            [CompletionResult]::new('-V', '-V ', [CompletionResultType]::ParameterName, 'Print version')
            [CompletionResult]::new('--version', '--version', [CompletionResultType]::ParameterName, 'Print version')
            break
        }
    })

    $completions.Where{ $_.CompletionText -like "$wordToComplete*" } |
        Sort-Object -Property ListItemText
}
```

For `zsh`:

```zsh
#compdef tex-fmt

autoload -U is-at-least

_tex-fmt() {
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
'-l+[Line length for wrapping \[default\: 80\]]:N:_default' \
'--wraplen=[Line length for wrapping \[default\: 80\]]:N:_default' \
'-t+[Number of characters to use as tab size \[default\: 2\]]:N:_default' \
'--tabsize=[Number of characters to use as tab size \[default\: 2\]]:N:_default' \
'--config=[Path to config file]:PATH:_files' \
'--completion=[Generate shell completion script]:SHELL:(bash elvish fish powershell zsh)' \
'-c[Check formatting, do not modify files]' \
'--check[Check formatting, do not modify files]' \
'-p[Print to stdout, do not modify files]' \
'--print[Print to stdout, do not modify files]' \
'-f[Format files and return non-zero exit code if files are modified]' \
'--fail-on-change[Format files and return non-zero exit code if files are modified]' \
'-n[Do not wrap long lines]' \
'--nowrap[Do not wrap long lines]' \
'--usetabs[Use tabs instead of spaces for indentation]' \
'-s[Process stdin as a single file, output to stdout]' \
'--stdin[Process stdin as a single file, output to stdout]' \
'--noconfig[Do not read any config file]' \
'-v[Show info messages]' \
'--verbose[Show info messages]' \
'-q[Hide warning messages]' \
'--quiet[Hide warning messages]' \
'--trace[Show trace messages]' \
'--man[Generate man page]' \
'--args[Print arguments passed to tex-fmt and exit]' \
'-r[Recursively search for files to format]' \
'--recursive[Recursively search for files to format]' \
'-h[Print help]' \
'--help[Print help]' \
'-V[Print version]' \
'--version[Print version]' \
'::files -- List of files to be formatted:_default' \
&& ret=0
}

(( $+functions[_tex-fmt_commands] )) ||
_tex-fmt_commands() {
    local commands; commands=()
    _describe -t commands 'tex-fmt commands' commands "$@"
}

if [ "$funcstack[1]" = "_tex-fmt" ]; then
    _tex-fmt "$@"
else
    compdef _tex-fmt tex-fmt
fi
```

Each script has one final newline after the displayed content.

## Spec 19

`--man` returns 0, writes nothing to stderr, exits without processing files,
and emits this exact roff text with one final newline:

```roff
.ie \n(.g .ds Aq \(aq
.el .ds Aq '
.TH tex-fmt 1  "tex-fmt 0.5.6" 
.SH NAME
tex\-fmt \- LaTeX formatter written in Rust
.SH SYNOPSIS
\fBtex\-fmt\fR [\fB\-c\fR|\fB\-\-check\fR] [\fB\-p\fR|\fB\-\-print\fR] [\fB\-f\fR|\fB\-\-fail\-on\-change\fR] [\fB\-n\fR|\fB\-\-nowrap\fR] [\fB\-l\fR|\fB\-\-wraplen\fR] [\fB\-t\fR|\fB\-\-tabsize\fR] [\fB\-\-usetabs\fR] [\fB\-s\fR|\fB\-\-stdin\fR] [\fB\-\-config\fR] [\fB\-\-noconfig\fR] [\fB\-v\fR|\fB\-\-verbose\fR] [\fB\-q\fR|\fB\-\-quiet\fR] [\fB\-\-trace\fR] [\fB\-\-completion\fR] [\fB\-\-man\fR] [\fB\-\-args\fR] [\fB\-r\fR|\fB\-\-recursive\fR] [\fB\-h\fR|\fB\-\-help\fR] [\fB\-V\fR|\fB\-\-version\fR] [\fIfiles\fR] 
.SH DESCRIPTION
LaTeX formatter written in Rust
.SH OPTIONS
.TP
\fB\-c\fR, \fB\-\-check\fR
Check formatting, do not modify files
.TP
\fB\-p\fR, \fB\-\-print\fR
Print to stdout, do not modify files
.TP
\fB\-f\fR, \fB\-\-fail\-on\-change\fR
Format files and return non\-zero exit code if files are modified
.TP
\fB\-n\fR, \fB\-\-nowrap\fR
Do not wrap long lines
.TP
\fB\-l\fR, \fB\-\-wraplen\fR \fI<N>\fR
Line length for wrapping [default: 80]
.TP
\fB\-t\fR, \fB\-\-tabsize\fR \fI<N>\fR
Number of characters to use as tab size [default: 2]
.TP
\fB\-\-usetabs\fR
Use tabs instead of spaces for indentation
.TP
\fB\-s\fR, \fB\-\-stdin\fR
Process stdin as a single file, output to stdout
.TP
\fB\-\-config\fR \fI<PATH>\fR
Path to config file
.TP
\fB\-\-noconfig\fR
Do not read any config file
.TP
\fB\-v\fR, \fB\-\-verbose\fR
Show info messages
.TP
\fB\-q\fR, \fB\-\-quiet\fR
Hide warning messages
.TP
\fB\-\-trace\fR
Show trace messages
.TP
\fB\-\-completion\fR \fI<SHELL>\fR
Generate shell completion script
.br

.br
[\fIpossible values: \fRbash, elvish, fish, powershell, zsh]
.TP
\fB\-\-man\fR
Generate man page
.TP
\fB\-\-args\fR
Print arguments passed to tex\-fmt and exit
.TP
\fB\-r\fR, \fB\-\-recursive\fR
Recursively search for files to format
.TP
\fB\-h\fR, \fB\-\-help\fR
Print help
.TP
\fB\-V\fR, \fB\-\-version\fR
Print version
.TP
[\fIfiles\fR]
List of files to be formatted
.SH VERSION
v0.5.6
.SH AUTHORS
William George Underwood, wg.underwood13@gmail.com
```
