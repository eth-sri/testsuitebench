# Universal Multi-Language Runner Specification

The required artifact is one executable file named exactly `executable`. All behavior below is observable behavior of that file. Language interpreters and compilers named below are harness-provided external commands; they are not additional artifacts to implement.

## Spec 1

`executable` is a command-line program that selects a programming language, obtains source from an inline argument, a file, standard input, or an interactive terminal, and runs that source with the selected language toolchain. Except for the C/C++ inline `\n` materialization described in Specs 20 and 21, source and paths are passed as argument/data values rather than evaluated as shell commands, so quotes, dollar signs, backticks, Unicode, spaces, brackets, and quote characters retain their meaning. Unless a later rule says otherwise, Python is the default language.

The program has three top-level outcomes: help/version display, one-shot execution, and an interactive REPL. Normal one-shot runs must not print runner banners or status messages; their stdout and stderr consist only of the executed program/toolchain output.

## Spec 2

Both `-h` and `--help`, when parsed as leading options, exit 0, write nothing to stderr, and write exactly the following UTF-8 text (including blank lines, spacing, and the final newline) to stdout:

```text
Universal multi-language runner and REPL

Usage: executable [OPTIONS] [ARGS]...

Arguments:
  [ARGS]...  Positional arguments (language, code, or file)

Options:
  -V, --version      Print version information and exit
  -l, --lang <LANG>  Explicitly choose the language to execute
  -f, --file <PATH>  Execute code from the provided file path
  -c, --code <CODE>  Execute the provided code snippet
      --no-detect    Disable heuristic language detection
  -h, --help         Print help
```

There is no subcommand/commands section. A leading help option takes precedence over later unknown options and prints help successfully.

## Spec 3

Both `-V` and `--version`, when parsed as leading options, exit 0, write nothing to stderr, and emit the same multiline metadata form to stdout. The first line begins `run-kit 0.3.2`; the output also contains all of these deterministic lines:

```text
run-kit 0.3.2
Universal multi-language runner and smart REPL
author: Esubalew Chekol <esubalewchekol6@gmail.com>
homepage: https://esubalew.et
repository: https://github.com/Esubaalew/run
license: Apache-2.0
```

It additionally has `commit:`, `built:`, and `rustc:` lines, each followed by nonempty build metadata, and ends with a newline. Version mode takes priority over execution options that follow it, so `--version -c CODE` displays metadata and does not execute `CODE`.

## Spec 4

The recognized options are exactly `-V`/`--version`, `-h`/`--help`, `-l`/`--lang`, `-f`/`--file`, `-c`/`--code`, and `--no-detect`. Before ordinary positional parsing begins, long value options support both a separate value and `--name=value`; `-lpython` is accepted as the joined short form. Short and long forms otherwise behave identically, and the `--lang`, `--file`, and `--code` options may appear in any order before ordinary source positionals begin. Immediately after a recognized positional language, the compatibility parser recognizes the separate-token forms `--code CODE` and `--file PATH`, but not their equals forms. In particular, `python --file=PATH` does not select file mode: the token reaches Python as its argument, which exits 2 and begins stderr with `unknown option --file=PATH`. Options are case-sensitive.

`--lang`, `--code`, and `--file` require one value. Repeating `--lang` or repeating `--code` is invalid. `--code` and `--file` are mutually exclusive. A literal `--` stops option parsing; tokens after it are positional values. A terminating `--` with no following values is harmless after valid `--code` input.

## Spec 5

Command-line syntax errors are written only to stderr and exit 2. Required exact forms include:

```text
error: a value is required for '--lang <LANG>' but none was supplied

For more information, try '--help'.
```

The same form applies to missing `--code <CODE>` and `--file <PATH>`. A leading short `-l`, `-c`, or `-f` with no value reports the corresponding canonical long placeholder in this same form. Repetition uses:

```text
error: the argument '--code <CODE>' cannot be used multiple times

Usage: executable [OPTIONS] [ARGS]...

For more information, try '--help'.
```

Substitute `--lang <LANG>` for a repeated language option. For an unknown option `X`, use:

```text
error: unexpected argument 'X' found

  tip: to pass 'X' as a value, use '-- X'

Usage: executable [OPTIONS] [ARGS]...

For more information, try '--help'.
```

Thus `--no-such-flag` and uppercase spellings such as `--LANG` are rejected in that exact style.

## Spec 6

Semantic CLI validation errors exit 1, write nothing to stdout, and end with a newline on stderr. The exact messages are:

```text
Error: --code/--inline cannot be combined with --file
Error: Inline code provided via --code must not be empty
Error: Unexpected positional arguments after specifying --code
Error: Unexpected positional arguments when --file is present
```

For the positional-language compatibility syntax described later, a missing value after positional `-c` is `Error: --code/--inline requires a code argument`; a missing value after positional `-f` is `Error: --file requires a path argument`; and extra values after positional `-f PATH` use `Error: Unexpected positional arguments after specifying --file`.

An exactly empty `--code ""` value is treated as if the option had no value: it exits 2 with the missing-`--code <CODE>` diagnostic from Spec 5. A nonempty string made only of spaces, tabs, or newlines exits 1 with `Error: Inline code provided via --code must not be empty\n`.

## Spec 7

The canonical registry contains exactly these 25 identifiers, regardless of whether their tools are installed:

```text
bash, c, cpp, crystal, csharp, dart, elixir, go, groovy, haskell, java, javascript, julia, kotlin, lua, nim, perl, php, python, r, ruby, rust, swift, typescript, zig
```

Language lookup trims leading/trailing whitespace and is ASCII-case-insensitive. It does not delete internal punctuation: arbitrary names such as `py_thon`, `py-thon`, `python with spaces`, or `python;ls` remain unknown. An empty language option is treated as a missing value. For an unknown normalized value `NAME`, exit 1 and emit exactly:

```text
Error: Unknown language 'NAME'. Available languages: bash, c, cpp, crystal, csharp, dart, elixir, go, groovy, haskell, java, javascript, julia, kotlin, lua, nim, perl, php, python, r, ruby, rust, swift, typescript, zig
```

## Spec 8

The following aliases resolve to the indicated canonical language in both one-shot selection and REPL language switching:

- Python: `python`, `py`, `py3`, `python3`.
- Bash: `bash`, `sh`, `shell`.
- C++: `cpp`, `c++`. The spelling `cxx` is not an alias: explicit one-shot selection reports it as an unknown language, `:cxx` reports `unknown command: :cxx. Type :help for help.`, and `:lang cxx` reports it as unsupported.
- Rust: `rust`, `rs`.
- Go: `go`, `golang`.
- JavaScript: `javascript`, `js`, `node`.
- Ruby: `ruby`, `rb`.
- C#: `csharp`, `cs`.
- Kotlin: `kotlin`, `kt`.
- Haskell: `haskell`, `hs`.
- Crystal: `crystal`, `cr`.

Aliases normalize to the canonical identifier for prompts and messages. For example, `:lang js` switches to `javascript`, and `:cr` switches to `crystal`.

## Spec 9

After leading options are parsed, positional values use this compatibility grammar:

1. If no explicit `--lang` was supplied and the first positional token is a known language name/alias, it selects that language and is removed from the source tokens. With an explicit `--lang`, later language-looking positional tokens are ordinary source/extra tokens; they are not consumed as redundant language selectors.
2. After a positional language, `-c`/`--code` and `-f`/`--file` select the corresponding source mode. The positional compatibility handling of short `-c` joins every following positional token with one ASCII space. Thus `python -c "print('a')" "print('b')"` submits the single invalid string `print('a') print('b')` and produces Python's native `SyntaxError`; it is not rejected as an extra-argument CLI error. Positional `-f PATH` means file input and permits no token after `PATH`. Missing-value and positional-file extra-value errors are defined in Spec 6.
3. If `--code` is present, no remaining positional values are allowed, including language names and aliases. Thus `--lang python --code "print('redundant')" py` exits 1 with `Error: Unexpected positional arguments after specifying --code\n`. If `--file` is present, no remaining positional values are allowed. The sole empty tail after `--` does not count as a value.
4. With no source option, one remaining path-like token is a file source; otherwise all remaining tokens are joined with one ASCII space and treated as inline code. Thus `python print(1 + 2)` executes the joined source `print(1 + 2)`, while a bare unknown word is Python code, not a subcommand. With explicit `--lang python`, the positional sequence `py` followed by `print('ok')` is submitted as `py print('ok')` and produces Python's native `SyntaxError` rather than consuming `py`.
5. `LANG -` and `-f -` explicitly select source-code input from stdin; an optional positional or explicit language may accompany `-f -`.

Once ordinary positional `ARGS` have begun, tokens such as `--version` and `--help` are source tokens rather than global options. Therefore `1 --version` and `1 --help` are attempted as joined Python source and fail as Python; `-- --help` likewise does not show help.

## Spec 10

A single positional token is path-like if it names an existing filesystem object, has a recognized source extension, begins with `/`, `./`, `../`, or `~/`, or contains `/` or `\`. Path-like input is treated as a file even if it does not exist; it must not be attempted as inline code. The executable does not expand `~` itself. Relative paths are resolved in the caller's current working directory, symlinks are followed normally, and absolute/long/Unicode/space/special-character paths are preserved as one path.

An existing file with no extension is a file. A non-path-like single token such as `definitely_not_a_real_subcommand_123` is inline Python source and consequently produces a Python `NameError`. Extra positional values after explicit file input are rejected; they are not passed as script arguments.

## Spec 11

When detection is enabled, file language detection is case-insensitive and extension-first. The tested mappings are:

- `.py`, `.pyw` to Python.
- `.sh`, `.bash`, `.zsh` to Bash.
- `.c` to C.
- `.cpp`, `.cc`, `.cxx`, `.hpp`, `.hxx` to C++.
- `.rs` to Rust; `.go` to Go; `.pl` to Perl.
- `.java` to Java; `.kt`/`.kts` to Kotlin; `.lua` to Lua; `.rb` to Ruby.
- `.jl` and `.julia` to Julia.
- `.js`, `.mjs`, `.cjs`, `.jsx` to JavaScript.

An explicit language always overrides an extension, including deliberately running Bash source stored in `.py` or Python source stored in `.sh`/`.txt`. A recognized extension wins over contradictory file contents. An unknown extension or no extension falls back to Python rather than inspecting ordinary file contents for another language.

## Spec 12

For inline or stdin source with no explicit language, enabled heuristic detection scans the text using case-sensitive signatures. Leading whitespace is tolerated and signatures may occur at the beginning of any line, not only line 1. Python signatures win over Bash/Lua signatures; Rust signatures win over C++ signatures; a C# namespace signature wins over C++ signatures; and C++ signatures win over C signatures. The tested signatures are:

- Python: a lowercase `import` statement (including dotted module names), `from ... import ...` (including `*` and relative-dot forms), or lowercase `def`/`class` followed by a valid identifier whose first character may be `_`. Comments/blank lines before a later signature do not prevent matching. Uppercase `DEF` is not this signature.
- C++: `#include <iostream>`, `#include <vector>`, `std::`, `using namespace std`, or the same `int`/whitespace/`main` form listed for C. Consequently `extern int puts(const char*);\nint\t main (void) { ... }` selects C++ rather than C.
- C: an angle-bracket `#include` on any line or `int` followed by whitespace and `main` followed by optional whitespace and `(`. Multiple spaces/tabs are accepted.
- Rust: `fn main` or a `use` declaration. An arbitrary non-main `fn` declaration is not a signature: `fn helper() {}` falls through to Python, exits 1 with empty stdout, and emits a Python `<string>` `SyntaxError: invalid syntax` on stderr.
- Go: `package main` or a `func main` declaration. An arbitrary non-main `func` declaration is not a signature: `func helper() {}` falls through to Python, exits 1 with empty stdout, and emits a Python `<string>` `SyntaxError: invalid syntax` on stderr.
- Bash: a Bash/sh shebang (including `/bin/bash`, `/bin/sh`, `/usr/bin/env bash`, and whitespace after `#!`), lowercase `export` or `read` followed by whitespace, a lowercase shell `echo` command, or `$(` command substitution.
- C#: a line beginning with `namespace` followed by an identifier and `{`. This takes priority even if a later line contains `using namespace std` or `std::`; in the harness, those overlap cases select C# and emit the missing-`dotnet` error from Spec 23.
- Lua: a line beginning with lowercase `print` followed by optional whitespace and `(`. Thus bare `print(6 * 7)`, `print('ok')`, and an uppercase non-Python `DEF` line followed by `print(...)` select Lua. In the harness they exit 1 with the missing-Lua message from Spec 23. The signature also applies after a long comment line, so an unqualified large source ending in `print('large-inline')` selects Lua rather than default Python.

If no signature matches, choose Python. For an overlap such as `use std::io;` plus `fn main()` whose text also contains `std::`, choose Rust. Detection only selects an engine; it does not rewrite the user's source.

## Spec 13

`--no-detect` disables both extension and snippet heuristics, then uses the explicit language if supplied and Python otherwise. Consequently Bash-looking stdin or a positional `.sh` file is attempted as Python under `--no-detect`. A Python file still succeeds because Python is also the default. The flag is compatible with explicit `--lang` and with every source mode.

## Spec 14

One-shot execution keeps child stdout and stderr separate and does not label, recolor, reorder within either stream, or truncate text output. Output is passed through lossy UTF-8 conversion rather than preserved byte-for-byte: when Python writes `bytes(range(256))` to stdout, bytes `0x00` through `0x7f` are unchanged and each standalone byte `0x80` through `0xff` is emitted as the three-byte UTF-8 encoding `0xef 0xbf 0xbd` of the replacement character. The resulting stdout is 512 bytes. Valid UTF-8 such as `snowman:☃` on stderr is preserved. The runner handles empty output, Unicode, single lines much larger than ordinary terminal widths, at least 10,000 output lines, and concurrent stdout/stderr without deadlock. Stderr output alone does not imply failure.

On successful child startup, the executable's exit status is the child's status, including 0 and explicit values such as 1, 3, 5, 7, 42, and 127. Syntax/runtime/compiler/linker failures remain nonzero. A child that loops forever remains running until the caller terminates/times out; the runner must not detach it or falsely report completion.

## Spec 15

Source transport depends on mode:

- Inline Python uses `python3 -c CODE`; inline Bash uses `/usr/bin/bash -c CODE`; analogous engines use their native inline or temporary-file mechanism. Any stdin supplied simultaneously remains the running program's data stdin.
- File mode gives interpreted languages the original path, so their diagnostics name that path. It does not change the current working directory.
- Source-stdin mode reads source from the caller's stdin and executes it as source. For Python this must retain Python's `<stdin>` diagnostic identity; for Bash a missing final newline is accepted.
- Empty source from stdin is a successful no-op for Python/Bash. Files with no final newline and CRLF Python files execute normally.

The child inherits the caller's working directory and ordinary process environment. In particular, relative file operations and `os.getcwd()` observe the caller's directory.

## Spec 16

When piped stdin supplies source without a `--file`/`-f` source option, the runner materializes it as UTF-8 text. This includes having no source arguments, supplying only `--lang python`, and using positional `python -`. Invalid UTF-8 in these forms exits 1 with exactly:

```text
Error: failed to materialize execution payload

Caused by:
    stream did not contain valid UTF-8
```

Python file-stdin mode is transported differently: `--lang python --file -` passes the original stdin byte stream to Python without runner UTF-8 validation. Given exactly the single byte `0xff`, it exits 1, writes nothing to stdout, and writes exactly the following native Python diagnostic to stderr (with a final newline):

```text
SyntaxError: Non-UTF-8 code starting with '\xff' in file <stdin> on line 2, but no encoding declared; see https://python.org/dev/peps/pep-0263/ for details
```

A NUL byte supplied as data stdin to inline code is preserved. A Python `.py` file consisting of `print('before')\n` followed by bytes `0x00 0xff` is an observed exception to textual validation: it exits 0, writes `before\n`, and writes no stderr. Very large but reasonable inputs are not artificially truncated: explicitly selected Python successfully executes a roughly 1 MiB stdin source. Without explicit selection, normal detection still runs first; a roughly 110 KiB comment followed by `print('large-inline')` selects Lua as specified in Spec 12.

## Spec 17

Python execution uses the harness-provided Python 3 interpreter and otherwise exposes normal Python 3 semantics without preprocessing. It must support multiline suites, imports and standard library modules, functions/closures/recursion, classes/inheritance/decorators, generators, async code, comprehensions, lambdas, context managers, exceptions, Unicode, collection/string operations, modern syntax such as f-strings and assignment expressions, and direct writes to stdout/stderr.

Inline diagnostics identify the source as `<string>`, stdin-source diagnostics as `<stdin>`, and file diagnostics by the original path. Tracebacks and warnings are forwarded verbatim. Python `sys.exit(N)` becomes executable status `N`. For a missing Python file, Python's own form is retained, including status 2 and text such as `/usr/bin/python3: can't open file '<absolute-or-supplied-path>': [Errno 2] No such file or directory`.

## Spec 18

Bash execution uses `/usr/bin/bash` and exposes Bash, not merely POSIX-sh, semantics. Inline, file, and source-stdin modes support variables/export, arrays, functions, conditionals/case, loops, arithmetic and parameter expansion, globbing, pipes/redirection/process substitution, command substitution/subshells, heredocs, test operators, environment access, and `set -e` behavior.

The final Bash command/pipeline determines status in the ordinary way. An explicit earlier `exit` stops later commands. Stdout/stderr remain separate. Bash diagnostics, including file paths and line numbers, are forwarded verbatim; for example an inline missing command is `/usr/bin/bash: line 1: NAME: command not found\n` and exits 127. A missing file `/nonexistent/file.sh` produces `/usr/bin/bash: /nonexistent/file.sh: No such file or directory\n`.

## Spec 19

C one-shot execution uses the harness-provided GCC toolchain, with warnings enabled and the math library linked. Source is placed in a newly-created directory named `/tmp/run-cSUFFIX`, where `SUFFIX` is exactly six ASCII alphanumeric characters, in a file named `main.c`; it is compiled to a binary named `run_c_binary` and executed. Compiler and linker stderr is forwarded verbatim and a compile/link failure exits 1. For the wrapped snippet `undeclared_function();`, the generated statement begins at line 5, column 5: stderr identifies `main.c:5:5`, warns about the implicit declaration, then reports the undefined reference, and the runner exits 1.

Full C programs must support normal GCC C features used by the suite: headers/preprocessor macros, multiple/helper/recursive/static/variadic functions, argc/argv, arrays and pointers, structs/unions/enums/typedefs, designated and multidimensional initializers, function pointers, allocation, `assert`, `snprintf`, integer wraparound, control flow, and libm functions. The compiled program's own status and stdout/stderr are propagated, including abort/assert diagnostics and nonzero `main` returns.

## Spec 20

C inline classification uses simple source text markers rather than lexical recognition. The contiguous substring `main(` marks the input as a translation unit even when it is a declaration, occurs inside a string or comment, or is the suffix of a larger identifier such as `mymain`. It does not match `main (` with intervening whitespace or `main2(`. An angle-bracket include is also a translation-unit marker.

If neither marker is present, place the inline text inside a generated `int main` body and append a successful return. This makes ordinary statement snippets executable, but also means `int main () { printf("Space before paren\\n"); return 0; }` is nested inside the generated function: it exits 0 without printing. Conversely, `int main(void);` is left unwrapped and fails linking with an undefined reference to `main`; `int main();\nprintf("This is not inside main\\n");` is left unwrapped and fails at the top-level `printf`; and string/comment/`mymain` inputs containing `main(` are likewise left unwrapped and produce compiler errors for a following top-level `printf`.

Before C inline source is written, backslash-newline escape text is interpreted in the observed command-line form. For an argument containing these literal characters:

```text
#include <stdio.h>\nint main() { printf("inline-c with \\n newlines\n"); return 0; }
```

the first `\n` becomes a source line break while `\\n` becomes the C `\n` escape. Execution exits 0, writes the following line with a final newline, and writes no stderr:

```text
inline-c with \n newlines
```

## Spec 21

C++ one-shot execution uses the harness-provided `g++` with warnings and C++17 support. It creates `/tmp/run-cpp<RANDOM>/main.cpp`, compiles a native temporary binary, runs it on success, forwards tool/program streams subject to the UTF-8 behavior in Spec 14, propagates program status, and exits 1 on compilation/link failure. The submitted translation unit is not given a second `main` when it already defines one; a translation unit with only a main declaration or no definition fails at link time.

C++ inline source performs the same observed backslash-newline materialization as C. For an argument containing these literal characters:

```text
#include <iostream>\nint main() { std::cout << "inline-cpp with \\n newlines" << std::endl; return 0; }
```

execution exits 0, writes the following line with a final newline, and writes no stderr:

```text
inline-cpp with \n newlines
```

Main detection must tolerate whitespace, newlines, comments, nested parameter parentheses, trailing-return syntax, and escaped/ordinary/raw string and character literals while rejecting `main` embedded in comments, literals, or larger identifiers. Valid C++17 constructs must pass through, including namespaces, classes/inheritance/virtuals, templates and fold expressions, lambdas, exceptions, smart pointers/move semantics, STL containers/algorithms/tuples/optional/variant, constexpr/if-constexpr, structured bindings, initializer forms, casts, attributes, and raw strings. Native g++ diagnostics for invalid syntax/types/access/ambiguity are forwarded with the temporary `main.cpp` path and source lines (actual comments are stripped from the prepared diagnostic source).

## Spec 22

Rust and Go have working one-shot inline and ordinary-file modes whenever their harness commands are present, but `--file -` does not successfully transport stdin for either engine. Perl has the tested inline and file modes:

- Rust source is compiled with `rustc` to a temporary executable and run. Complete inline and ordinary-file `fn main()` programs, ordinary functions, bindings, vectors, string operations, and compiler failures use native Rust behavior. For `--lang rust --file -` with a complete main program on stdin, the executable instead compiles an empty crate, exits 1, writes no stdout, and rustc reports that the `main` function was not found in crate `run_snippet`.
- Go source is compiled/run with `go`. Complete inline and ordinary-file `package main` programs, imports, functions, loops, and variables/slices use native Go behavior. For `-lgo -f -` with a complete program on stdin, the executable exits 1, writes no stdout, and emits `Error: failed to invoke /usr/local/go/bin/go to run -`, followed by a `Caused by:` section ending `No such file or directory (os error 2)`.
- Perl source uses `perl` in inline or file form and preserves native output/status.

Temporary build artifacts are not printed. Build diagnostics go to stderr, runtime stdout/stderr remain separate, and program exit status is propagated.

## Spec 23

Known languages are registered even when their external command is absent. Missing-tool failures are clean status-1 runner errors rather than “unknown language.” The exact messages required for these unavailable engines are:

```text
Error: Java support requires the `javac` compiler. Install the JDK from https://adoptium.net/ or your vendor of choice and ensure it is on your PATH.
Error: Kotlin support requires the `kotlinc` compiler. Install it from https://kotlinlang.org/docs/command-line.html and ensure it is on your PATH.
Error: Lua support requires the `lua` executable. Install it from https://www.lua.org/download.html and ensure it is on your PATH.
Error: Julia support requires the `julia` executable. Install Julia from https://julialang.org/downloads/ and ensure `julia` is on your PATH.
Error: C# support requires the `dotnet` CLI. Install the .NET SDK from https://dotnet.microsoft.com/download and ensure `dotnet` is on your PATH.
```

Each is one line with a final newline. In the tested environment, starting missing Ruby or JavaScript tools reports exactly `Error: No such file or directory (os error 2)\n`. Selecting any registered language in the REPL must still succeed and update the prompt without first requiring its compiler/interpreter.

## Spec 24

With a source specified, execution is noninteractive. With no explicit source and stdin connected to a non-terminal, stdin is source code; immediate EOF is an empty default-Python program and exits 0 silently. With no source and a terminal stdin/stdout, enter the REPL. `--lang LANGUAGE` with a terminal enters that language's REPL. No-argument non-terminal invocation must not hang.

## Spec 25

On a terminal, the REPL initially writes exactly:

```text
run universal REPL. Type :help for commands.
python>>> 
```

The default active language is Python. The normal prompt is `<canonical-language>>> ` and the continuation prompt for a multiline Python/C/C++ entry is `... `. Input is terminal-echoed by the line editor. Empty or whitespace-only input returns to the appropriate prompt without an error and does not damage session state. `:exit`, `:quit`, and terminal EOF leave cleanly.

## Spec 26

The REPL command `:help` displays this command reference and returns to the active prompt:

```text
Commands:
  :help                 Show this help message
  :languages            List available languages
  :lang <id>            Switch to language <id>
  :detect on|off        Enable or disable auto language detection
  :reset                Reset the current language session
  :load <path>          Execute a file in the current language
  :exit, :quit          Leave the REPL
Any language id or alias works as a shortcut, e.g. :py, :cpp, :csharp, :php.
```

`:load` takes only the first whitespace-delimited token after the command as its path; it does not treat the entire unquoted remainder as one path. For `:load /tmp/.../loaded file.txt`, Python is invoked on `/tmp/.../loaded`, reports that file missing, the REPL displays `[exit code 2] (<elapsed>ms)`, and the Python prompt returns.

## Spec 27

`:lang ID` and `:ALIAS` switch language. Switching to another language prints `switched to <canonical-id>`; selecting the already-active language prints `already using <canonical-id>`. The next prompt uses the canonical id. This switching behavior applies to all 25 canonical identifiers even when their tools are unavailable, as well as the aliases in Spec 8.

`:languages` prints `available languages: ` followed by the exact sorted canonical list from Spec 7, comma-and-space separated, then returns to the prompt. Terminal wrapping may visually split the long line but must not alter its logical text.

Auto-detection starts enabled. `:detect off`, `:detect on`, and `:detect toggle` change it and print respectively `auto-detect disabled` or `auto-detect enabled`. Disabled detection leaves input in the manually selected language. With detection enabled, detecting another engine permanently changes the active language and next prompt, and first writes `[auto-detect] switching OLD → NEW`. For example, entering `echo detected-shell` at `python>>> ` writes `[auto-detect] switching python → bash`, executes the line, and returns to `bash>>> `. Entering `print('alive')` instead switches from Python to Lua; in the harness the missing Lua executable then produces the Spec 23 error and terminates the REPL rather than returning to a prompt.

## Spec 28

The REPL accumulates supported incomplete constructs until complete. Python compound statements such as a function definition show `... ` prompts and a blank line completes the block. C and C++ input consisting of a lone angle-bracket include displays `... ` and waits for another line; C++ input can continue through a following complete program. Perl and Rust multiline brace-delimited definitions are likewise accumulated.

Bash does not accumulate incomplete compound commands. It executes each submitted physical line immediately with the replayed session. Entering `if [ 1 -eq 1 ]` or `for n in one two; do` therefore produces Bash's `syntax error: unexpected end of file`, displays `[exit code 2] (<elapsed>ms)`, and returns directly to `bash>>> ` rather than showing `... `.

Only output newly produced by the latest evaluation is displayed; replaying accumulated session source must not redisplay old output. Carriage-return pairs in session output become `\n`, and lone `\r` bytes are removed. Before redisplaying the prompt, the C++ REPL terminates program output with a newline when the program omitted one: a multiline program that writes exactly `Hello` is presented as `Hello\ncpp>>> `, not `Hellocpp>>> `.

## Spec 29

The Python REPL preserves assignments, imports, function/class definitions, and other successful state between evaluations. A bare expression displays Python `repr` (for example `2 + 2` prints `4`, and a returned string prints with quotes); statements and assignments do not print an expression result. Multiline definitions remain callable later.

`:reset` clears Python state and prints `session for 'python' reset`. A later reference to an old name produces the native `NameError`. Failed evaluations do not terminate the REPL. Their traceback is displayed, followed by `[exit code N] (<elapsed>ms)`, and the prompt returns.

## Spec 30

The Bash REPL preserves successful variables, exported values, arrays, functions, and statements across inputs. It displays only new stdout/stderr from the latest input. A failing command reports native Bash stderr plus `[exit code N] (<elapsed>ms)`, remains usable, retains earlier successful state, and is rolled back so it is not rerun later. Explicit subshell failure statuses such as 42 and command-not-found status 127 are shown.

`:reset` clears Bash variables, arrays, functions, and accumulated statements while keeping the REPL alive; it prints `session for 'bash' reset`. Bash snippets without final newlines execute correctly; incomplete compound prefixes have the immediate-error behavior from Spec 28.

## Spec 31

The evaluated C REPL behavior is a compile-and-replay session with prompt `c>>> `. Successful top-level declarations persist for later inputs. It must handle integer, character, and floating variables (including `extern`, `static`, `const`, `volatile`, `signed`, `unsigned`, `short`, and `long` forms), arrays, typedefs, enum constants, function prototypes/definitions with one- or multiword return types, and global variables. Preprocessor definitions such as `#define MAX 100`, `#ifdef`/`#endif`, and `#pragma` are retained in the appropriate top-level portion of the replayed source. A lone submitted `#include <math.h>` is not accepted as a complete entry: it displays `... ` and waits for more input.

A nonempty single-line input without a trailing semicolon that is not a declaration/directive is evaluated as an expression and its value is printed. This includes integer/float arithmetic, function calls, array indexing, bitwise/logical/comparison operators, casts, ternary and comma operators, `sizeof`, parentheses, negatives, hex, and octal literals. Integer results are decimal, C truth values are `0`/`1`, and floating values use a normal readable numeric representation. Semicolon-terminated statements/declarations do not auto-print. The C session supplies `__print(value)` for statement snippets; the tested `if (1) { __print(99); }` input prints 99 and is executed inside the generated main rather than retained as a top-level item. A declaration missing its semicolon is not repaired or retried: `int val = 77` produces a compiler error at the generated `return 0`, displays `[exit code 1] (<elapsed>ms)`, and is rolled back; entering `val` next reports it undeclared and again exits 1.

An input containing its own real `main` is compiled and run as a standalone program without access to session declarations; it does not erase the session. A failed top-level item is rolled back while earlier valid state remains usable. Empty and whitespace-only input is ignored. Successful earlier declarations remain available for all later evaluated sequences above.

## Spec 32

The evaluated C++ REPL behavior uses prompt `cpp>>> ` and a C++17 preamble that makes the standard facilities needed by the evaluated inputs available, including unqualified `vector`, `cout`, and `endl`. Template function definitions, enum definitions/values, and `using` type aliases persist to subsequent inputs and can be instantiated or printed. A submitted `#include <iostream>` by itself displays `... ` and waits for continuation; it is not accepted as a complete redundant entry. Empty input is ignored. The central `:help` text is exactly the text in Spec 26.

## Spec 33

The Perl REPL uses prompt `perl>>> ` and a persistent strict-mode session with `say` available. Bare arithmetic or value expressions are evaluated and printed (a trailing semicolon makes input a statement instead), while `my`/`our`/`state` statements, `use`/`no` pragmas, and `sub` declarations persist. A semicolon-less `print "Hello\\n"` therefore writes `Hello\n` and then displays print's return value `1\n`. Multiline blocks execute once complete. Empty input is ignored.

`:reset` prints `session for 'perl' reset` and clears variables/declarations. Referring to a cleared lexical under strict mode reports Perl's native `Global symbol ... requires explicit package name` diagnostic and `[exit code 255]`, after which the REPL remains responsive.

## Spec 34

The evaluated Go REPL behavior uses prompt `go>>> ` and supplies the ordinary `fmt` environment needed by snippets. A successful short variable declaration such as `x := 42` persists, and entering `x` later displays 42. A top-level `type Point struct { X, Y int }` definition persists: the later input `p := Point{X: 10, Y: 20}; fmt.Println(p.X)` prints 10. By contrast, `p := Point{X: 10, Y: 20}; p.X` does not auto-print its final expression; Go reports `p.X (variable of type int) is not used`, the REPL displays `[exit code 1] (<elapsed>ms)`, and returns to `go>>> `. Empty and whitespace-only input is ignored, after which `fmt.Println("alive")` still executes normally.

## Spec 35

The Rust REPL uses prompt `rust>>> ` and preserves successful `let` bindings, `use` declarations, function definitions, and struct definitions. Bare expressions are automatically printed using a suitable Rust debug/display form, so arithmetic, variable references, method results, and values such as collection length are visible. Multiline functions are accumulated until their closing brace. Standard-library uses such as `HashMap` and `Arc` work in subsequent entries.

`:reset` prints `session for 'rust' reset`, clears prior bindings/items/imports, and leaves the session usable; a later old-name reference reports native rustc failure plus `[exit code 1]`. Empty input is ignored.

## Spec 36

For any REPL evaluation that launches a compiler/interpreter and returns nonzero, display its stdout/stderr, then a status line of the form `[exit code N] (<elapsed>ms)`, and return to the prompt unless the engine itself cannot be started. Elapsed time is a nonnegative integer. Temporary Python REPL scripts reside in a directory beginning `/tmp/run-python-repl` and are named `session.py`, so tracebacks have that form. State and recovery behavior after an error follow the individual language sections above.

## Spec 37

Interactive input may be syntax-highlighted when terminal color is supported. Language switching must have a highlighting mapping for every canonical language and supported alias; TypeScript uses JavaScript-like highlighting, while Julia and Elixir may use plain text. `NO_COLOR` set to any value disables ANSI escape sequences. `TERM=dumb` also disables highlighting even when `NO_COLOR` is absent and `COLORTERM=truecolor`: entering `2 + 2` is echoed plainly, prints `4`, and contains no ANSI escape sequence. With `TERM=dumb` and no `COLORTERM`, highlighting is likewise disabled.

## Spec 38

The executable must be safe under repeated and parallel invocations. Every compiled/session instance uses a unique temporary workspace, does not collide with another invocation, and cleans up when practical. It must not modify source files. One failed compilation, runtime exception, invalid option, empty input, unusual path, or large stream must not hang the parent process or contaminate later independent runs.
