# Clarified specification for `executable`

`executable` is the `argc` 1.23.0 command-line program: a compiler/runtime for Bash command-line interfaces described by specially formatted comments, and a task runner for `Argcfile` scripts. All behavior below is part of the required interface. Text output is UTF-8 and, unless explicitly stated otherwise, ends with a newline. Paths and arbitrary argument values must be preserved without lossy decoding.

## Spec 1

The executable shall dispatch on the first argument when it is an internal mode beginning with `--argc-`. The supported modes, and only these modes, are:

```
--argc-eval FILE ARGS...
--argc-create RECIPES...
--argc-run FILE ARGS...
--argc-build FILE [OUTPATH]
--argc-mangen FILE OUTDIR
--argc-completions SHELL CMDS...
--argc-compgen SHELL FILE WORDS...
--argc-export FILE
--argc-parallel FILE ARGS...
--argc-script-path
--argc-shell-path
--argc-help
--argc-version
```

`--argc-version` writes exactly `argc 1.23.0`. `--argc-help` exits successfully and writes exactly this discoverability text, including layout and final blank line:

```
A bash cli framework, also a bash-based command runner - https://github.com/sigoden/argc

USAGE:
    argc --argc-eval <FILE> <ARGS~>            Use `eval "$(argc --argc-eval "$0" "$@")"`
    argc --argc-create <RECIPES~>              Create a boilerplate argcfile
    argc --argc-run <FILE> <ARGS~>             Run an argc-based script
    argc --argc-build <FILE> <OUTPATH?>        Generate bashscript without argc dependency
    argc --argc-mangen <FILE> <OUTDIR>         Generate man pages
    argc --argc-completions <SHELL> <CMDS>     Generate shell completion scripts
    argc --argc-compgen <SHELL> <FILE> <ARGS>  Generate completion candidates
    argc --argc-export <FILE>                  Export command line definitions as json
    argc --argc-parallel <FILE> <ARGS~>        Run functions in parallel
    argc --argc-script-path                    Print current argcfile path
    argc --argc-shell-path                     Print current shell path
    argc --argc-help                           Print help information
    argc --argc-version                        Print version information

```

An unrecognized internal option fails with status 1 and stderr `Unknown option \`OPTION\``. Successful utility modes do not add diagnostics to stderr.

## Spec 2

When the first argument is not an internal mode, the executable operates as an `Argcfile` task runner. It searches the current directory and then each parent for the closest file whose name is one of `Argcfile.sh`, `Argcfile`, `argcfile.sh`, `argcfile`, or the extensionless uppercase name `ARGCFILE`; the closest match wins. At each directory, if `ARGC_SCRIPT_NAME` is set, first look for that exact value and, when it does not already end in `.sh`, that value followed by `.sh`. A custom name found in that directory is selected in preference to a default recognized name there. If neither custom candidate exists in that directory, still consider the ordinary recognized names there before continuing to its parent; a missing custom name does not disable or postpone the default-name search. Thus, in a directory containing `Argcfile.sh` whose output is `first`, `ARGC_SCRIPT_NAME=absent argc` runs `Argcfile.sh`, writes `first`, and exits 0. Only when no directory supplies either kind of script, fail with status 1 and `Argcfile not found, try \`argc --argc-help\` for help.` on stderr. Otherwise resolve the discovered script to an absolute path, change cwd to its parent, set `ARGC_PWD` to the caller's original working directory as detailed in Spec 20, and execute it through Bash with all original arguments and environment values. Propagate its stdin, stdout, stderr, file effects, and exact exit status. An invocation without a task therefore causes the script's generated root help to appear on stderr and normally succeeds.

## Spec 3

The source language is ordinary Bash plus directive comments. Recognize a directive after optional leading whitespace and `#`, optional whitespace, then `@describe`, `@version`, `@cmd`, `@alias`, `@arg`, `@option`, `@flag`, `@env`, or `@meta`. Ignore unrelated comments and Bash text for interface purposes, but scan Bash function declarations in the forms `name() {`, `name () {`, and names containing `-` or `::`. A consecutive directive block containing `@cmd` and immediately associated with a function describes that command/function; root parameter directives belong before the first function declaration. After any completed function declaration, including an unannotated helper or an annotated command, a later `@arg`, `@flag`, or `@option` cannot start a new root block and requires an associated `@cmd`. An orphan parameter directive at source line `N` is rejected respectively as `@arg(line N) shouldn't be here, @cmd is missing?`, `@flag(line N) shouldn't be here, @cmd is missing?`, or `@option(line N) shouldn't be here, @cmd is missing?`. Thus a command function followed by a would-be root argument or flag is rejected, and a helper function followed by `# @option --item[...]` and then an unannotated `main` does not attach that option to `main`; at source line 4 its eval output is `echo 'Error: @option(line 4) shouldn'\''t be here, @cmd is missing?'` followed by `exit 1`, and compgen consequently returns status 0 with empty stdout/stderr rather than invoking the helper or serializing candidates. Blank comment lines and subsequent comment lines not starting with `@` extend a description until a non-comment source line ends the block. Preserve declaration order throughout help, export, completion, and man-page generation. A malformed recognized directive is a specification error with its one-based source line. An unknown directive has the exact diagnostic `@TAG(line N) is unknown tag`; this includes dotted forms such as `@cmd.child`, which at line 2 emits `echo 'Error: @cmd.child(line 2) is unknown tag'` followed by `exit 1`. For example, `# @unknown value` on line 2 emits `echo 'Error: @unknown(line 2) is unknown tag'` followed by `exit 1`.

`@describe TEXT` supplies the root short description and its following comment continuation lines supply the long description. `@cmd TEXT` marks the following function as a subcommand and supplies its description. A bare `@cmd` is valid. Dotted compact tags do not declare children; use an annotated `parent::child` function. Ordinarily a `@cmd` without a corresponding function reports `@cmd(line N) missing function?`; this includes an earlier unmatched directive in a consecutive pair. The exception is one final `@cmd` at end of source, whether bare or described: it is accepted as a bodyless subcommand whose name is the source's derived root name and whose exported `command_fn` is null. Thus a source consisting only of `# @cmd` successfully renders root help with a same-named bodyless command. For `minimal.sh` ending in `# @cmd This command has no body`, export succeeds and contains a subcommand named `minimal`, description `This command has no body`, and `"command_fn": null`.

## Spec 4

Command names are derived from function paths. A top-level function `foo_bar` has canonical command name `foo_bar` and also gets automatic alias `foo-bar`; do not create that alias for a leading-underscore internal-style name such as `_foo`. Hyphens in function names remain hyphens. `parent::child` declares `child` below `parent`, and arbitrarily deep `::` nesting is supported. Every declared nested command must have its parent command. The executed Bash function, and the exported `command_fn` when the command is a runnable leaf, use the original complete function name, including `::`; namespace export is specified in Spec 24.

`@alias a,b,c` adds comma-separated aliases to the command associated with that block. Matching an alias selects the real command and function. Aliases and command names must be unique among siblings and must not conflict with relevant function names. An alias conflict at line `N` with a command or alias says exactly `@alias(line N) conflicts with cmd or alias at line M`; it does not use “already exists” wording. For a conflict with a canonical command name, `M` is the function-declaration line, not its preceding `@cmd` line. For example, a command annotation on line 1, `one() { ...; }` on line 2, and conflicting alias on line 4 reports `@alias(line 4) conflicts with cmd or alias at line 2`. A nested function missing its parent says exactly `NAME(line N) lack of parent command`, where `NAME` is the complete `::`-qualified function name and `N` is its function-declaration line; for example, `nonexistent::child()` on line 3 produces `nonexistent::child(line 3) lack of parent command`. The pseudo-subcommand `help` is automatically available for any command with subcommands. In the scope where it appears, it uses only the next token as an immediate-child target: `help child` shows that child's help, and an invalid immediate target is a choice error. To navigate one level deeper, first select the parent and invoke its pseudo-command, as in `parent help child`, or select the descendant normally and append `--help`, as in `parent child --help`. A root-level `help parent child` does not recursively consume `child`; after selecting `parent` as its immediate target it ignores the remaining token and shows the parent help, including `USAGE: demo parent <COMMAND>` rather than the child help.

## Spec 5

`@flag [SHORT] LONG[MODIFIERS] [ENV-BINDING] DESCRIPTION` declares a zero-value parameter. Either spelling may be absent; spellings may begin with `-`, `--`, or one `+`, and multi-character single-dash spellings are valid. The parameter id comes from the long spelling when present, otherwise the short spelling. Remove leading `-` signs, but replace a leading `+` with the identifier prefix `plus_`: for declarations such as `+v +verbose` and `+o +output`, the variables are `argc_plus_verbose` and `argc_plus_output`. A token beginning `++` is not a second plus-style option spelling; it begins the description. Consequently, `@flag +v ++verbose` declares only `+v`, treats `++verbose` as its description, and `+v` sets `argc_plus_v=1`. Hyphens, dots, and other non-shell identifier characters become `_` in the Bash variable. The variable is `argc_ID`.

A plain flag is unset when absent and is scalar `1` when present. A `*` suffix makes it repeatable and its scalar value is the occurrence count. A trailing `+` is not a supported flag modifier when it is the only spelling: `# @flag --force+ Force` on line `N` produces the eval-safe source error `echo 'Error: syntax error at line N'` followed by `exit 1`. If a valid short-only declaration precedes such a token, however, parsing stops after the short spelling and treats the would-be long token as description text. Thus `# @flag -v --verbose+ Verbose mode` declares only `-v`, with description `--verbose+ Verbose mode`; it is valid for eval and man generation, and `--verbose` is not accepted. This does not affect a leading-plus spelling. For example, declared `+trace` is accepted only as `+trace` and sets `argc_plus_trace=1`, not `argc_trace`; `--trace` is unexpected. A non-repeatable flag used twice is an error. A flag passed as `--flag=value` is an error: `error: flag \`--flag\` don't accept any value`. Short and long spellings assign the same variable.

## Spec 6

`@option [SHORT] LONG[MODIFIERS/DEFAULT/CHOICE] [ENV-BINDING] [VALUE-NOTATIONS] DESCRIPTION` declares a value-taking parameter. It uses the same identifier derivation as Spec 5, including the `plus_` prefix for a leading `+`. An environment binding token must precede every explicit value notation; after a notation, `$NAME` is description text and the exported `env` is null. An ordinary option accepts `--name value` and `--name=value`. Assignment-only syntax is selected by a trailing `:` on the declared spelling, but the accepted assignment remains `--name=value`; `--name:value` is an unexpected argument, and the separated `--name value` form fails for an incorrect number of values. An ordinary option has exactly one value. Its default notation is the id converted to uppercase COBOL case (for example `api-endpoint` -> `API-ENDPOINT`); standalone explicit notations such as `<FILE>`, `<SRC> <DST>`, `<VALUE*>`, `<VALUE+>`, and `<VALUE?>` control the displayed name and minimum/maximum number of values. Multiple notation tokens yield a Bash array. `?`, `*`, and `+` on a notation mean zero-or-one, zero-or-more, and one-or-more values respectively. A fixed list such as `<X> <Y>` consumes exactly that many values. A notation token with an appended default is not recognized as an explicit notation. In particular, `# @option -o --output $OUTPUT <FILE>=none Output` is parsed as a single-spelling `-o` option: export has `id:"o"`, `long_name:"-o"`, `short_name:null`, `describe:"--output $OUTPUT <FILE>=none Output"`, `notations:["O"]`, `default:null`, and `env:null`.

An option-name `*` makes the option repeatable and accumulates all occurrences in an indexed array; `+` makes occurrences required and accumulating. A comma directly after the modifier (`*,` or `+,`) splits every supplied occurrence on comma and flattens the results; an alternate single-character delimiter can appear after the modifier, such as `*:`. A `~` option consumes every remaining token without interpreting later flags. A prefixed declaration such as `-D-*` exports the effective spelling `-D`, with `prefixed:true` and `multiple_occurs:true`. The suffix after that effective spelling is the associative key: `-DFOO=bar` and `-DFOO bar` create key `FOO`, while `-D-one 1` creates key `-one`, not `one`. Consequently, reading `argc_D[one]` after the latter yields an empty value. If no following value or same-token `=value` exists, the value is `1`. Do not interpret `-DFOO=bar` as an unknown option or require `bar` to be a separate token. Prefixed options cannot bind an environment variable.

## Spec 7

`@arg NAME[MODIFIERS/DEFAULT/CHOICE] [ENV-BINDING] [<NOTATION>] DESCRIPTION` declares a positional parameter in source order. With no modifier it is optional and scalar; `!` is required scalar; `*` is optional variadic; `+` is required variadic; and `~` captures all remaining positionals as an array, including tokens that resemble flags once capture begins. The legacy-looking token `NAME...` has no special variadic meaning: it is a scalar positional whose id retains the dots, whose notation is `NAME...`, and whose normalized Bash variable ends in three underscores (for example `item...` becomes `argc_item___`). The displayed notation otherwise defaults to the uppercased name and may be replaced only by an angle-bracket token such as `<TEXT>`. A bare token is the beginning of the description, not a notation: `@arg input FILE Input file` exports notation `INPUT` and description `FILE Input file`.

Variadic positionals are distributed so later scalar/required positionals can still receive values. With two variadics, tokens before `--` can belong to the first and tokens after the separator to the second where the declaration makes that split meaningful. A literal `--` ends option parsing, so following `-file`, `--input.txt`, and negative numbers are positional values. It is normally not assigned, but a terminated `~` positional captures the separator itself along with the remaining tokens. For example, with `@flag --yes`, required `head!`, and `tail~`, invocation `start -- --yes -3 --input.txt` leaves the flag unset, assigns `start` to `head`, and assigns exactly `--`, `--yes`, `-3`, and `--input.txt` to `tail`, in that order. A variadic positional consumes option-looking values without requiring `--`: for example, `cmd_multi_arg --o1 -o2 -3` assigns all three values to the variadic and forwards them to its handler. A command scope that declares no positionals retains otherwise unmatched ordinary tokens as undeclared positionals and forwards them to a selected handler, but it does not retain an unknown option-looking token. Thus a root containing only `@option --oa`, invoked as `--oa v1 v2`, sets the option to `v1` and forwards `v2`; adding `--odd` makes the invocation fail status 1 with `error: unexpected argument \`--odd\` found` and the handler is not run. In contrast, once a command declares one or more finite, nonvariadic positionals, values beyond that declared capacity are errors. Empty strings, Unicode, newlines, quotes, `$`, backticks, command-substitution text, backslashes, and spaces are distinct values and must survive round-trip unchanged.

## Spec 8

Static choices are written `[a|b|c]`; `[=a|b|c]` additionally defaults to the first member. Pipes inside an angle-bracket value notation do not create a choice: `@arg mode <fast|slow>` accepts `other` and stores it unchanged. A trailing `@choice a b c` is likewise description text, not a postfix choice declaration; export leaves `choice` null. Choices created by the bracket syntax are case-sensitive. Every `|` is a separator even when preceded by `\`; backslashes remain literal rather than escaping the separator, and surrounding single quotes are removed from a choice. Thus `[a\|b|c\\d|'quoted'|#hash|-x|a/b]` has the possible values `a\`, `b`, `c\\d`, `quoted`, `#hash`, `-x`, and `a/b`: it rejects `a|b`, `c\d`, and `'quoted'`, while accepting the corresponding literal values just listed. Validate every scalar or array element of an actual bracket choice.

Dynamic choices are written ``[`function`]``. Obtain their lines by launching the source script through the internal eval invocation `___internal___ FUNCTION ...`; do not extract a Bash function body and execute it directly. The source must itself reach its argc activation for the named function to run. Consequently, if that re-entry does not successfully invoke argc, the function contributes no lines even if its body would have printed values. A validating choice then has an empty choice set: supplied values `prod` for `<ENVIRONMENT>` and `us-west-2` for `<REGION>` are each rejected, with the diagnostic ending in `  [possible values: ]`. ``[?`function`]`` uses that function for completion but skips runtime validation. For a directive in a source position accepted under Spec 3, dynamic choice validation sees the parameter state and command arguments established so far; this does not make a post-helper orphan directive valid.

An invalid value reports `error: invalid value \`VALUE\` for \`NOTATION\`` followed on the next line by `  [possible values: a, b, c]`. Use an option's angle-bracket notation, an optional positional's square-bracket notation, and an environment-specific label as appropriate. Runtime validation treats each trimmed output line from a dynamic-choice function as the complete candidate value; it does not split a tab-separated description from that value. Thus candidate lines `dev<TAB>Development` and `prod<TAB>Production` reject the plain input `prod` and report those complete tab-bearing lines in the possible-values list; the literal argument `prod<TAB>Production` validates. A nonvalidating `[?\`function\`]` choice still accepts arbitrary input. Runtime validation never adds a shell-completion acceptance space to a candidate. For example, a function line `level:` makes the possible-value text exactly `[possible values: level:]`, not `[possible values: level: ]`.

## Spec 9

A literal default follows `=` in the option or positional parameter token (`--host=localhost`, `name=World`). For an option, `<PORT>=8080` is not notation-with-default syntax; the combined token is not recognized as an explicit notation, as detailed in Spec 6. A trailing `@default VALUE` is description text and does not set a default. A backtick default, such as ``--output=`default_fn` ``, means invoke the Bash function only if no CLI or environment value is supplied, provided the declaration is in a valid source position under Spec 3. Preserve that form literally in successful eval Bash: emit ``argc_output=`default_fn` `` and use the same backtick command substitution in `argc__positionals` and the handler call, rather than converting it to `"$(default_fn)"`. Quote and shell-escape arbitrary literal default data safely. Precedence is CLI value, then a bound environment value (including an explicitly present empty string), then the literal/dynamic default. A default embedded in choices via `[=first|...]` follows the same precedence. An optional parameter with no source and whose spelling is absent remains unset. In contrast, explicitly supplying a zero-value option such as `--maybe <VALUE?>` immediately before another option defines its scalar as the empty string.

## Spec 10

`@env NAME[!|=DEFAULT|CHOICES] DESCRIPTION` declares an environment variable. `!` requires the variable to be present; an explicitly exported empty value counts as present. Defaults and static/dynamic choices use the inline syntax of parameters. Tokens such as `@default` or `@choice` later on the directive are part of the description and do not create defaults or choices. On success, existing values remain intact, defaults are exported only when absent, and optional absent variables may remain unset. An environment declaration whose value already exists is not re-emitted as an `export NAME=value` line in eval output and is not placed into the decoded `ARGC_VARS` restore program; the value remains available through the inherited process environment. Environment declarations at a parent are inherited by child commands; child declarations may add variables and override a parent declaration for that scope. Duplicate names in the same scope are specification errors. Preserve the declared environment name literally for lookup, diagnostics, and generated `export` statements; punctuation is not normalized to `_`. Consequently, with `# @env HAS-DASH=ok`, generated evaluation attempts `export HAS-DASH=ok`, Bash reports ``export: `HAS-DASH=ok': not a valid identifier``, and `$HAS_DASH` remains empty. Required missing environments are reported together under:

```
error: the following required environments were not provided:
  NAME
```

An invalid environment choice says `error: invalid value \`VALUE\` for environment variable \`NAME\`` and lists possible values.

## Spec 11

Appending `$$` to a flag, option, or positional binds it to an automatically derived environment name: uppercase the id and replace non-alphanumeric characters with `_`. `$NAME` binds it explicitly. For an option with explicit notations, this binding token must occur before the first notation. `@env NAME` and `@delimiter X` later in the directive are description text and have no binding or delimiter effect. CLI values override valid inline bindings. Multiple parameters may read the same environment variable. For an environment-bound flag, `1` and `true` mean present/true, while `0` and `false` mean absent/false; any other value reports that the environment has an invalid value for the flag unless an explicit CLI occurrence overrides that binding. Repeatable options with a delimiter encoded in their option modifier split a valid environment binding into arrays and validate each member. Help displays `[env: NAME]` after the description/default information. The JSON export stores a syntactically recognized environment name in the parameter's `env` field; `$OUTPUT` after `<FILE>`, for example, is description text and exports `env:null`.

Only a single-valued `@env` declaration is valid; combinations that make it multiple are a source error. Binding an environment to a prefixed option is a source error whose exact message is `@option(line N) is invalid, cannot bind env with prefixed options`. Assignment, prefix, or delimiter syntax cannot be combined with multiple explicit value notations. Their exact messages are respectively `@option(line N) is invalid, cannot combine assign and multiple notations`, `@option(line N) is invalid, cannot combine prefix and multiple notations`, and the intentionally misspelled `@option(line N) is invalid, cannot combine delmiter and multiple notations`.

## Spec 12

Metadata is declared as `@meta KEY [VALUE]`. The root shorthand `@version V` has the same runtime version behavior as `@meta version V`, but differs in JSON export: `@meta version V` is retained in the root `metadata` object, whereas `@version V` is represented only by the root `version` field. Required semantics are:

- `version V` sets command version output and enables the root `-V`/`--version` flag. Absent versions render as `0.0.0` where a version string is needed. A bare `@meta version` is invalid: at line `N` it emits `echo 'Error: @meta(line N) invalid version value'` and then `exit 1`.
- `author`, `license`, and arbitrary metadata keys are retained for JSON export.
- `binname NAME` overrides the derived root display name.
- `man-section N` changes all generated man-page suffixes and `.TH` sections; default is `1`.
- `combine-shorts` enables clustered declared short flags such as `-abc`.
- `inherit-flag-options` makes root flags/options available at descendant commands and marks them inherited in export, except that a child declaration with the same id/spelling overrides the parent declaration once parsing has entered that child scope. For an occurrence after the subcommand token, the child parameter's choices and description win rather than forming a duplicate or retaining the parent's validation. The override is not applied retroactively to an occurrence parsed before the subcommand token; that occurrence retains the parent declaration and validation.
- `default-subcommand [NAME]` is accepted as metadata but does not select the annotated command or named child. A suffix such as ` (default)` in an `@cmd` description is likewise only description text and does not select that command. For a root named `tool` with metadata value `chosen` and children `chosen` and `other`, positional-looking input `value` fails with status 1 and `error: \`tool\` requires a subcommand but 'value' is not one of them`, followed by `  [subcommands: chosen, other]`. This metadata is accepted even when it occurs below a parent positional declaration. For the source lines `# @arg one`, `# @meta default-subcommand child`, `# @cmd`, and `child() { :; }`, eval succeeds; root help includes both `[ONE]` under `ARGS:` and `child` under `COMMANDS:`.
- `require-tools a,b` or space-separated names records required external commands.
- `dotenv [PATH]` enables dotenv loading, defaulting to `.env` beside/from the script execution context.
- `symbol +name` (or `symbol @name`) defines a leading symbolic argument such as a toolchain selector. A dynamic choice function is allowed only as ``symbol +name[`function`]``. An inline static list is not valid symbol syntax: `symbol +toolchain[stable|beta|nightly]` produces `@meta(line N) invalid symbol value`; compgen's forgiving protocol therefore returns status 0 with empty output for that source.

Reject an invalid symbol value at specification parsing time. Because a description suffix is not a declaration, `default-subcommand` metadata and another command described with ` (default)` coexist without a source conflict; neither changes dispatch.

## Spec 13

Before normal command execution, `require-tools` checks each named tool with the effective `PATH`; if any is absent, the generated code exits 1. In eval output it emits the ordinary assignments through `argc__positionals`, then one blank line, this exact helper and call, another blank line, and only then the selected handler:

```bash
_argc_require_tools() {
    local tool missing_tools=()
    for tool in "$@"; do
        if ! command -v "$tool" >/dev/null 2>&1; then
            missing_tools+=("$tool")
        fi
    done
    if [[ "${#missing_tools[@]}" -gt 0 ]]; then
        echo "error: missing tools: ${missing_tools[*]}" >&2
        exit 1
    fi
}
_argc_require_tools not-found1
```

Replace `not-found1` with the declared tool words in their effective order.

`dotenv` reads the requested file if it exists and silently does nothing if it does not. Read `KEY=value` lines, skip empty/comment/malformed lines, strip matching single or double quotes around values, preserve values containing `=`, and never override a variable already present in the process environment. Loaded values are exported before defaults, bindings, and command execution. After `export ARGC_VARS=...` and before `argc__args`, eval output emits this exact helper and invokes it with the configured path (`.env` by default):

```bash
_argc_load_dotenv() {
    local env_file="$1" env_vars=""
    if [[ -f "$env_file" ]]; then
        while IFS='=' read -r key value; do
            if [[ "$key" == $'#'* ]] || [[ -z "$key" ]]; then
                continue
            fi
            if [[ -z "${!key+x}" ]]; then
                env_vars="$env_vars $key=$value"
            fi
        done < <(cat "$env_file"; echo "")
        if [[ -n "$env_vars" ]]; then
            eval "export $env_vars"
        fi
    fi
}
_argc_load_dotenv .env
```

## Spec 14

Command-line parsing allows declared options before or after positionals and, under `inherit-flag-options`, on either side of a subcommand. Placement determines which same-spelling declaration validates an inherited option: before the subcommand it uses the parent declaration, while after the subcommand it uses a child override. For a parent `--global[a|b]` and child `--global[x|y]`, `--global a child` succeeds and retains `a`, `--global x child` fails with `error: invalid value \`x\` for \`<GLOBAL>\`` and `[possible values: a, b]`, while `child --global x` succeeds and `child --global a` fails against `[possible values: x, y]`. Without `combine-shorts`, only exact spellings match. With it, a cluster expands into known zero-argument short flags, increments repeatable members, and rejects the entire original cluster if any member is unknown. A short-named subcommand may be the first member of such a cluster: if `-s` is a subcommand declaring `-a` and `-b`, `-sab` selects function `-s` and sets both child flags.

A negative numeric token is a positional value without requiring `--` only in a command scope having no declared flags/options: a required `count` positional by itself receives scalar `-456`. Once the scope declares any flag or option, a negative token retains option-like parsing. Consequently, with option `-n/--number` and required positional `<VALUE>`, both `-n -42 -100` and `-n=-42 -100` fail, at `-42` and `-100` respectively, as `error: unexpected argument \`VALUE\` found`. Assignment syntax still permits the negative option value itself (`-n=-42`). Unknown nonnumeric option-like tokens are errors unless they can be retained by a declared variadic positional under Spec 7; that rule permits values such as `--o1` and `--enable`. Merely declaring no positionals does not permit them. An `=` inside an option value is data after the first assignment separator. A parameter that is not repeatable errors on its second occurrence with `error: the argument \`--name\` cannot be used multiple times`.

When a command requires a subcommand, missing input says `error: \`BIN\` requires a subcommand but one was not provided`; an invalid name says `error: \`BIN\` requires a subcommand but 'NAME' is not one of them`; both add `  [subcommands: a, b]`. `BIN` is the full display path joined with hyphens, not spaces: nested command `demo parent` is rendered as `demo-parent`. An option-like input not captured under Spec 7 says `error: unexpected argument \`VALUE\` found`. Too many positional values under a finite declared capacity use the same unexpected-argument form. An option with too few/many values formats the diagnostic operand from the effective option spelling and its displayed notations. An ordinary option separates its spelling and notations with spaces: `# @option --copy <SRC> <DST>` invoked as `--copy one` fails with `error: incorrect number of values for \`--copy <SRC> <DST>\``. An assignment-only option joins its spelling to the first notation with `=`: `# @option --mode:` invoked as `--mode fast` fails with `error: incorrect number of values for \`--mode=<MODE>\``. Both failures have status 1.

## Spec 15

Validate required values after parsing. Missing required options are reported before missing positionals; if any required option is missing, only that category is reported. Otherwise report all missing required positionals in declaration order. The exact common form is:

```
error: the following required arguments were not provided:
  --name <NAME>
  <INPUT>
```

Required repeatable/variadic values append `...` to their display. Choice checks occur for each supplied or environment-derived element and stop at the first invalid value. Parser errors and help/version are not ordinary process failures in `--argc-eval`: they are rendered as Bash that prints to stderr and executes `exit 1` (or `exit 0` for help/version), so the `executable --argc-eval ...` process itself exits 0 whenever it could read and interpret the source. Every runtime parser/validation diagnostic and every help/version response is encoded in stdout with this exact here-document form, including when `TEXT` has only one line; the opener ends with one literal ASCII space after the closing quote:

```
command cat >&2 <<-'EOF' 
TEXT
EOF
exit N
```

`TEXT` is the complete rendered text, without an extra blank line before the terminating `EOF`, and `N` is `0` for help/version or `1` for an error. Do not replace this public eval output with equivalent per-line `printf` commands.

## Spec 16

Every command accepts an automatic help action. An explicit flag using `--help` does not shadow that long action: invoking it renders help to stderr and does not call the handler, although the explicit declaration can change the displayed spelling/description (for example, `-?, --help` with `Custom help switch`). A user flag using the short spelling `-h`, however, shadows only automatic short help: `-h` sets that flag's `argc_*` variable while `--help` and `-help` remain help actions. The same collision rule applies to user `-V` versus automatic version. A root command also gets a version flag; descendants only get version when applicable. Automatic spellings are `--help`, `-help`, and `-h` when unclaimed; version similarly uses `--version`, `-version`, and unclaimed `-V`. Acceptance does not imply that an automatic control is rendered in help or man pages. Help is written to stderr when the emitted eval code is evaluated. Its deterministic plain-text layout is:

1. short/long command description, then a blank line;
2. `USAGE: path ...` with `[OPTIONS]`, required/optional/multiple positional notation, or `<COMMAND>`;
3. optional `ARGS:`, `OPTIONS:`, `COMMANDS:`, and `ENVIRONMENTS:` blocks in that order, separated by blank lines;
4. entries in declaration order with columns padded to align descriptions;
5. automatic help/version entries at the end of `OPTIONS:`, but only when that command has at least one user-declared flag or option.

Required values use `<X>`, optional values `[X]`, and multiples add `...`. Positionals, commands, environment declarations, and metadata do not create an `OPTIONS:` block. Thus positional-only commands show `ARGS:` and omit automatic rows entirely, both an environment-only root and an environment-only subcommand omit `OPTIONS:` even though help is accepted, and a subcommand-only root's help ends after `COMMANDS:` and its following blank line. When automatic rows are rendered, their descriptions are `Print help`/`Print version` if at least one user-declared flag or option has a nonempty description; if all user flag/option descriptions are empty, the automatic row descriptions are empty too. Except for the standalone built-script behavior in Spec 23, every rendered help document ends in a blank line: direct runner help therefore ends with two newline bytes, while eval heredoc source has exactly one empty line between the last rendered entry and `EOF`. A subcommand-only root invoked without a subcommand shows help and exits 0. A command with a `main` handler may execute it instead. At the immediate parent's command scope, `command help child` and `command child --help` show child-specific usage; the pseudo-command form does not consume a deeper descendant path, as detailed in Spec 4. `TERM_WIDTH`, when present, controls wrapping of long descriptions; continuation comment lines and explicit paragraphs are preserved, and no-wrap behavior is deterministic when width is absent/large.

When version is requested for a script, render `DISPLAY-NAME VERSION`, not the bare version. For `metadata.sh` containing version `2.1.0`, `-V` emits a heredoc whose body is exactly `metadata 2.1.0`, followed by `exit 0`.

## Spec 17

`--argc-eval FILE ARGS...` reads the interface without requiring the source to be valid Bash syntax outside recognized declarations. The displayed root name is the basename with the final extension removed (`foo.sh` -> `foo`, `test.script.sh` -> `test.script`), unless overridden by metadata. A missing FILE argument returns process status 0 and stdout:

```
echo 'Error: No script file provided'
exit 1
```

A missing/unreadable file is likewise converted to shell code whose logical error text surrounds the path with single quotes: `Error: Failed to load script at 'PATH'`, followed by `exit 1`. For example, `/nonexistent/script.sh` produces exactly:

```
echo 'Error: Failed to load script at '\''/nonexistent/script.sh'\'''
exit 1
```

Source-specification errors are shell code of the form `echo 'Error: MESSAGE'` and `exit 1`. Shell single quotes inside messages must be escaped with the same split-quote form.

## Spec 18

On a successful match, eval mode emits shell-safe Bash assignments in this order: user `argc_*` scalar/indexed/associative variables in declaration/match order; `argc__args`; `argc__fn` when a handler is selected; any other applicable dispatch/context variables; `argc__positionals`; then hook/handler calls. `argc__args` is an indexed array whose first value is the derived command name and whose rest are the original CLI tokens. `argc__positionals` contains the final positional values (defaults included when applicable). For a selected handler set `argc__fn` to its complete Bash function name and call it with the positional array, not option values. Root `main` and namespace `parent::main` are implicit handlers. A parent function that has children is a namespace unless it is also the selected handler under these rules.

Before these lines, emit `export ARGC_VARS=BASE64`, where `BASE64` is standard base64 without line wrapping of a semicolon-terminated restore program. It contains the emitted variable assignments in the same order and, when hooks apply, the bare `_argc_before;` and `_argc_after;` calls in their execution order; it does not contain the selected ordinary handler call. The restore serialization has one observed newline edge case: the visible assignment preserves a newline-bearing scalar exactly, but its `ARGC_VARS` fragment keeps only the text before the first newline and drops that assignment's closing quote. With `NAME` containing the two lines `line1` and `line2`, visible output is:

```bash
argc_name='line1
line2'
```

The decoded program instead starts exactly `argc_name='line1;` before the next assignment. This permits `--argc-parallel` children to restore ordinary parent state while reproducing the reference's newline behavior.

All shell literals use the reference Bash quoting. Safe words remain bare; this safe set includes `FILE!`, so that value is emitted exactly as `argc_config=FILE!`, not single-quoted. Empty strings are `''`, and embedded single quotes use the standard split-quote form. A prefixed option map is emitted as a declaration followed by one assignment per key in encounter order, for example:

```bash
declare -A argc_X
argc_X["foo"]=bar
argc_X["baz"]=qux
```

The decoded restore program uses the corresponding exact fragments `declare -A argc_X;argc_X["foo"]=bar;argc_X["baz"]=qux;`. Do not collapse this into a single `declare -A argc_X=(...)` assignment. Every indexed-array assignment has one literal space after `(` and before `)`: a populated array is `name=( value1 value2 )` and an empty array is `name=(  )`. The same spaces are present in the decoded `ARGC_VARS` program. Do not compact either form to `name=(value1 value2)` or `name=()`.

Ordinary successful dispatch ends after the direct hook/handler lines described above. Do not add `argc__cmd_fn`, an `argc__status` wrapper, conditional `declare -F` calls, or a final `exit "$argc__status"` to that output. The additional context variables named in Spec 19 belong to internal completion/choice-function evaluation when relevant, not to every ordinary command dispatch.

## Spec 19

If `_argc_before` is a function in the source, emit the bare command line `_argc_before` after variables have been initialized and before a handler. Do not wrap it in a runtime `declare -F` test. Invoke `_argc_after` as the bare line `_argc_after` after an actual handler. If no normal handler exists, `_argc_before` still runs but `_argc_after` does not. A selected function is emitted as its bare function name followed by the serialized positional arguments between the two hook lines. Thus a selected `cmd` produces, in order, `_argc_before`, `cmd`, `_argc_after`; a root with only the before/after definitions produces only `_argc_before`. Internal choice-function execution (`___internal___ FUNCTION ...`) initializes the partial command/parameter context, calls `_argc_before`, invokes the requested function with the relevant positional values, calls `_argc_after`, and then exits so the script body does not continue. Context variables include `argc__cmd_arg_index`, `argc__cmd_fn`, and `argc__option` when relevant.

## Spec 20

`--argc-run FILE ARGS...` locates `/usr/bin/bash` (or the validated shell from Spec 34) and executes the script with the supplied arguments, preserving argument boundaries, stdin, output, and exit code. No file argument fails with status 1 and stderr `No script file provided`. A nonexistent file is allowed to fail through Bash (normally status 127 and Bash's standard “No such file or directory” message). Passing `/` fails status 1 with stderr `Unable to retrieve the script dir from '/'`. When FILE is an absolute path whose basename is one of the recognized Argcfile runner names, export `ARGC_PWD` as the caller's original working directory and change cwd to the script's parent before executing it; preserve a pre-existing `ARGC_PWD` rather than overwriting it. Relative and non-runner scripts retain the caller's cwd and do not spuriously set `ARGC_PWD`. Syntax errors and handler exit/return statuses pass through unchanged.

## Spec 21

`--argc-create RECIPES...` creates, without overwriting, the file named exactly by `ARGC_SCRIPT_NAME` (do not append a second `.sh`) or, when unset, `Argcfile.sh`. Before creating the default file, check the recognized name variants from Spec 2; if any exists, treat that existing variant as the collision. On success create the file without adding execute permission (under the required environment its mode is `0644`) and print `NAME has been successfully created.`. With no recipes its exact content is:

```
#!/usr/bin/env bash

set -e

# See more details at https://github.com/sigoden/argc
eval "$(argc --argc-eval "$0" "$@")"
```

For every recipe, in input order and separated by one blank line, insert before the final comment:

```
# @cmd
RECIPE() {
    echo TODO RECIPE
}
```

Recipe text is inserted literally; even names containing spaces are accepted and may consequently produce invalid Bash. If the destination exists, do not alter it, fail status 1, and write `Already exist ABSOLUTE_PATH` to stderr.

## Spec 22

`--argc-build FILE [OUTPATH]` converts the input to one standalone Bash file that implements Specs 3–19 without invoking `argc` at runtime. With no FILE fail status 1 and stderr `No script file provided`. A load failure has this exact multiline structure:

```
Failed to load script at 'PATH'

Caused by:
    No such file or directory (os error 2)
```

With no OUTPATH write the complete built file to stdout. If OUTPATH ends with `/` or denotes a directory, recursively create it if needed and place a file having the input basename inside. Otherwise create missing parent directories and write that file. Successful file-output mode has empty stdout. Overwrite an existing output file. A newly created file is executable; when overwriting, preserve the existing file's permission bits (in particular, do not add execute permission to a pre-existing non-executable file).

## Spec 23

Build preserves the entire original source byte-for-byte except for its argc activation region. Replace `eval "$(argc --argc-eval "$0" "$@")"` (and accepted equivalent command-substitution spellings) with a generated region bracketed exactly by:

```
# ARGC-BUILD {
# This block was generated by argc (https://github.com/sigoden/argc).
# Modifying it manually is not recommended
...
# ARGC-BUILD }
```

If such a generated block already exists, replace it rather than nesting/duplicating it. Preserve the original shebang; a source without one remains buildable. The generated block is native Bash and must not delegate at runtime to Python, an encoded copy of another implementation, or `argc`. It defines `_argc_run`, one deterministic usage routine per command, version and parser routines, argument-taking/positional-matching helpers, any choice/environment/tool checks used by that source, `_argc_maybe_flag_option`, and `_argc_die`, and ends by calling `_argc_run "$@"`. Feature helpers are present when needed: dotenv metadata emits `_argc_load_dotenv`, and required-tool metadata emits `_argc_require_tools`. Output generation is deterministic in source declaration order.

The byte-for-byte conformance examples in `fixtures/` are normative, not illustrative. For every `build-*.sh` input there, `executable --argc-build INPUT` must equal the correspondingly named `build-*.golden`; `build-write.golden` is the exact file written for `build-write.sh`. These pairs define the generated template for all inputs, not only the listed samples: every matching source construct must use the corresponding helper body, relative helper position, indentation, blank lines, quoting, usage-routine form, and source-order substitution from the golden files. A behaviorally equivalent alternative template does not conform. The pairs also fix the final newline and feature-specific code for nested commands, dotenv, hooks/tool checks, environment bindings/delimiters, defaults, required parameters, choices, and default subcommands. Their exact invocations are listed in `fixtures/README.md`.

The generated file's visible runtime behavior equals eval mode except for these observed standalone-runtime rules:

- `--help` and `--version` write their rendered text directly to stdout, leave stderr empty, and exit 0; they do not reproduce eval mode's stdout shell snippet or its eventual stderr stream. Built help omits the eval rendering's terminal empty line and ends with exactly one newline byte. In particular, a built `tool` having only required positional `input!` emits exactly `USAGE: tool <INPUT>\n\nARGS:\n  <INPUT>\n` for `--help`.
- When a built script having one required positional such as `<INPUT>` is invoked without it, it exits 1 with empty stdout and exact stderr `error: the required environments \`<INPUT>\` were not provided`. This standalone diagnostic is not the ordinary eval-mode required-arguments block.

## Spec 24

`--argc-export FILE` writes pretty-printed JSON using two-space indentation and a final newline. No FILE fails with status 1 and `No script file provided`; unreadable input uses the load-error form in Spec 22. Before writing JSON, export validates that every function named by a dynamic default or dynamic choice is declared in the source and stops at the first missing reference. It fails status 1 with empty stdout and `FUNCTION(line N) is missing` on stderr: a missing `default_out` referenced on line 5 produces `default_out(line 5) is missing`, while after that function is supplied, a missing `complete_out` referenced on line 2 produces `complete_out(line 2) is missing`. The root and each nested command is an object with fields in this order:

```
name, describe, version, aliases, flag_options, positionals,
envs, subcommands, [metadata on root when any metadata exists], command_fn
```

`name` is the derived name, `describe` defaults to `""`, `version` and `command_fn` are string or null, and collections are arrays. `subcommands` is a recursively nested tree in declaration order, not a flattened list. `metadata` is an insertion-ordered object retaining declared root `@meta` entries, including `version`, `binname`, author, license, custom keys, and man-section. The separate `@version` shorthand populates the root `version` field but is not retained in `metadata`: `@version 2.5.0` followed by `@meta author Ada`, `@meta custom some value`, and `@meta binname demo` exports root `"version":"2.5.0"` and exactly `"metadata":{"author":"Ada","custom":"some value","binname":"demo"}` in declaration order. By contrast, `@meta version 2.5.0` appears both as root `version` and as metadata. `@meta binname demo` both changes root `name` to `demo` and retains `"binname":"demo"` in `metadata`. A runnable leaf exports its complete Bash function name in `command_fn`. A namespace command with children exports `command_fn:null` even when a same-named Bash function was declared; a root without an applicable `main` likewise exports null. JSON string escaping must preserve special characters.

## Spec 25

Every exported flag/option object has, in this order, fields:

```
id, long_name, short_name, describe, flag, notations, required,
multiple_values, multiple_occurs, num_args, delimiter, terminated,
prefixed, assigned, default, choice, env, inherited
```

Use null for a missing short name/environment/delimiter/default/choice. A flag has `flag:true`, no notations, and `num_args:[0,0]`. An ordinary option has `flag:false`, a default uppercase notation, and `[1,1]`; derive other minimum and maximum bounds from its explicit notations. Encode an unbounded maximum as the numeric sentinel `32767`, not JSON null; for example, a terminated `--rest~ <ARG>` exports `num_args:[1,32767]`. An exported positional has fields `id, describe, notation, required, multiple, delimiter, terminated, default, choice, env`. Its exported `notation` removes the angle brackets from an explicit notation and uppercases its contents without interpreting punctuation: `<fast|slow>` exports `"notation":"FAST|SLOW"`. An exported environment has `id, describe, required, default, choice, inherited`.

A literal default is `{"type":"Value","value":"..."}` and a function default is `{"type":"Fn","value":"function"}`. Static choice is `{"type":"Values","data":[...]}`. Dynamic choice is `{"type":"Fn","data":["function",true]}` where the boolean says validation is enabled; it is false for `?` dynamic choices. An option-name delimiter modifier implies both repeated occurrences and multiple flattened values: for `--tags+,`, export has `required:true`, `multiple_values:true`, `multiple_occurs:true`, and `delimiter:","`. Automatic help/version flags use ids `help`/`version` and the effective spellings described in Spec 16. Their descriptions are `Print help`/`Print version` exactly when at least one user-declared flag or option has a nonempty description; positionals alone do not trigger these descriptions, so a positional-only command exports its automatic help with `"describe":""`.

## Spec 26

`--argc-mangen FILE OUTDIR` requires both arguments. Missing FILE yields `No script file provided`; for a readable FILE, missing OUTDIR yields `No output dir`; both fail status 1 on stderr. FILE is loaded before the missing-OUTDIR check, so `--argc-mangen x` when `x` does not exist reports the Spec 22 load-error form for `x`, not `No output dir`. An existing non-directory also fails status 1 and writes exactly:

```
Invalid output dir

Caused by:
    Not an directory
```

Recursively create a missing output directory. Generate one page for the root and every namespace/leaf command, in preorder. The filename is the full command path joined with `-`, plus `.SECTION`. For every written file print `saved PATH` in the same order.

Every page begins `.TH UPPERCASE-PAGE-NAME SECTION  "page-name VERSION" `, where the page name preserves underscores inside command names and joins command-path components with hyphens. The `.TH` line uses literal hyphens in both its uppercase title and its quoted page-name/version argument; for the minimal leaf it is exactly `.TH MAN-MINIMAL-SIMPLE 1  "man-minimal-simple 0.0.0" `. It is followed by `.SH NAME`, `.SH SYNOPSIS`, and applicable sections. An `OPTIONS` section exists when the command has at least one user-declared flag, option, or positional; a page with none has no such section. Whenever it exists, it includes automatic help and applicable version controls after the user flags/options and before positional entries. Use `0.0.0` in `.TH` for a command lacking a version; include `.SH VERSION` only for an explicitly versioned command. Outside the `.TH` line, escape rendered hyphens as `\-`; bold command/option syntax with `\fB...\fR` and italic value notation with `\fI...\fR`. A missing description makes NAME contain only the command name.

## Spec 27

Man-page synopsis uses the full space-separated command path. A namespace shows `<COMMAND>`; otherwise include `[OPTIONS]` when it has user-declared flags/options and then positionals. In SYNOPSIS, positional notation is plain roff text rather than italic markup: required positionals are `<NAME>`, optional positionals `[NAME]`, choice notation is likewise plain (for example `<START|STOP|RESTART>`), and a multiple adds exactly one `...` (for example `<FILES>...`). The OPTIONS section uses `.TP` per user flag/option, then automatic controls, then positionals. It shows short plus long names, `=VALUE`, defaults as `[default: value]`, descriptions after `.br`, and choices as `[\fIpossible values: \fRa, b]`. Automatic controls use the same `.TP` structure: for the usual double-dash form the help header is exactly `\fB\-h\fR, \fB\-\-help\fR`, and version is analogous. When Spec 16 gives the automatic control a nonempty description, follow the header with `.br` and `Print help`/`Print version`; otherwise omit that body. A required repeatable option displays `=<\fINAME\fR>...`; an optional repeatable option displays `=[\fINAME\fR]...`. Each SUBCOMMANDS entry is exactly `.TP`, then the unbolded cross-reference `full\-hyphenated\-path(SECTION)`, then the one-line description. For example:

```roff
.TP
complex_script\-main_cmd(1)
Main command
```

The environment section heading is exactly `.SH "ENVIRONMENT VARIABLES:"`, including the quotes and colon. Every environment name is italicized; a required name places the marker after the italic reset. For example, required `API_KEY` is exactly `\fIAPI_KEY\fR*`, followed by `.br` and its description. Defaults and choices follow the same conventions.

The one-line short description is used only on the NAME line and subcommand listing. Create `.SH DESCRIPTION` only when the stored command description contains a newline (a continuation line or paragraph); a one-line `@describe` or `@cmd` description does not create it. Therefore a minimally described leaf page can end immediately after SYNOPSIS. When DESCRIPTION is present, place `.br` immediately after `.SH DESCRIPTION`, before its first text line, and another `.br` between every pair of original description lines/paragraphs.

## Spec 28

`--argc-completions SHELL CMDS...` accepts the generated-script shells `bash,elvish,fish,nushell,powershell,xonsh,zsh,tcsh`. It also accepts `generic` as a successful no-output request. A missing shell fails status 1 with:

```
Usage: argc --argc-completions <SHELL> [CMDS]...
```

A supplied but invalid shell fails status 1 with:

```
The provided shell is either invalid or missing, must be one of bash,elvish,fish,nushell,powershell,xonsh,zsh,tcsh
```

It emits a deterministic native completion adapter named `_argc_completer` (or `argc-completer` for Elvish). The adapter reconstructs words up to the cursor, preserving quoted/escaped words and an empty current word, then calls `argc --argc-compgen SHELL "" WORDS...`. Registration always includes `argc` first and then each `CMDS` item in supplied order. Absolute/path command strings are retained literally.

The complete adapter source is a public byte-for-byte interface. For the canonical invocation `executable --argc-completions SHELL simple`, output must equal `fixtures/completion-SHELL.golden` for Bash, Zsh, Fish, Nushell, PowerShell, and Elvish, including indentation and final newline. Those observed templates and exact invocations are normative as described in `fixtures/README.md`. For another `CMDS` list, preserve the template and replace only its shell-specific registration list: Bash/Zsh use their backslash-continued final registration; Fish and Elvish iterate `argc` then supplied commands; PowerShell's array starts with `"argc"`; Nushell embeds no command list. Xonsh extends `ARGC_XONSH_SCRIPTS`. Tcsh emits this exact newline-terminated statement for `argc` and then repeats it for every supplied command in order, replacing only the command word:

```tcsh
complete argc 'p@*@`echo "$COMMAND_LINE'"''"'" | xargs argc --argc-compgen tcsh ""`@@';
```

## Spec 29

`--argc-compgen SHELL FILE WORDS...` is a forgiving machine protocol: insufficient arguments, an invalid shell, an unreadable nonempty FILE, an invalid completion kind, or no matches all return status 0 with empty stdout/stderr. At least two `WORDS` are required: the first is always the invoked command and the last is the partial token. A call having only `""`, `l`, or `list` after FILE therefore returns empty output rather than treating that lone word as a partial or selected command. `FILE=""` means complete the built-in `argc` interface. In the adapter-shaped invocation `--argc-compgen bash "" argc 1 ""`, if cwd contains `Argcfile.sh`, output is exactly `Argcfile.sh ` plus newline: at this state the discovered script filename itself is the candidate, rather than that script's task candidates. Accept the completion adapters' optional numeric cursor-position control field between the invoked word and the partial. Parse intervening complete words with the same command matcher as eval, but do not execute a target command. Command aliases are accepted in those complete words. They are also emitted for command completion, but only the first comma-separated alias is offered: a command `cmd1` with `@alias one,o` produces `cmd1` and then `one`, but not `o`, before the next declared command.

Suggest only items valid at that state: child commands (plus pseudo-command `help`), currently usable flags/options, or values for the current option/positional. Prefix-filter candidates. Preserve declaration order for child commands and their first aliases, then append `help` with description `Show help for a command`. Candidate families are also gated by the partial token: an empty partial offers child commands or positional/value candidates, but does not offer any option spelling; option spellings, including automatic help/version, appear when the partial begins with their `-` or `+` marker. If an empty partial at a resolved command has only flags/options and therefore yields no state-specific candidates, generic completion falls back to path completion and emits exactly `__argc_value=path<TAB>/color:default`. For a partial `-`, process declared controls in declaration order and emit each control's long spelling before its short spelling, then emit automatic controls long before short. At a root declaring `-v --verbose` and `-f --file`, but no version metadata, the exact order is nevertheless `--verbose`, `-v`, `--file`, `-f`, `--help`, `-h`, `--version`, `-V`. At the versionless `opts` subcommand containing long-only `--verbose` and `--output`, the corresponding order is only `--verbose`, `--output`, `--help`, `-h`. Nonrepeatable options already consumed are omitted; after `--file input.txt` at that root, the partial `-` produces `--verbose`, `-v`, `--help`, `-h`, `--version`, `-V`. Repeatable options and variadic positional choices remain available. Both short and long spellings are emitted when the typed prefix could match them. Under `inherit-flag-options`, a child declaration with the same id/spelling replaces the inherited parent declaration for that child; its own choice set and description are used. Thus parent `--ob[a|b]` and child `--ob[x|y]` accept `--ob x` in the child.

Assigned option completion matches the text following `--opt=`/`--opt:` but emits the bare matching choice, without the assignment prefix. Thus generic completion of `--mode=s` for `[fast|slow]` is exactly `slow<TAB>/color:default`. Delimited completion likewise matches only the segment after the last delimiter and excludes values selected in earlier segments, but emits each remaining bare choice without the already-entered prefix or delimiter. The candidates are marked as accepting no trailing space. For `--language+,[python|rust|javascript|go]`, generic completion at `python,r` emits the bytes `rust\0<TAB>/color:default\n`; at `python,` it emits `rust`, `javascript`, and `go` in declaration order, each with that NUL no-space marker and generic color field. `--` changes completion to positional-only. A partial beginning `-` selects the option-candidate family before dynamic positional values are prefix-matched, so a signed dynamic positional candidate is not offered at that partial. In the `long-desc` fixture, an empty partial emits `--short`, `--long`, and `--no-parens`, but partial `--s` returns status 0 with empty stdout/stderr rather than emitting `--short`. Command aliases navigate to the same definition as their canonical command; `default-subcommand` metadata has no navigation effect, consistent with Spec 12. For a valid source layout, completion functions execute through the internal eval path so they see parsed `argc_*`, `argc__args`, `argc__positionals`, command function/index, and current option context. If the directive is orphaned after a helper function, Spec 3 applies instead and compgen returns no candidate output.

When completing an external command with no explicit FILE, search each colon-separated directory in `ARGC_COMPLETIONS_PATH` in order for `COMMAND.sh` and command/subcommand-specific paths such as `COMMAND/SUBCOMMAND.sh`. Use the first applicable definition. If no definition resolves the state, fall back to path completion rather than crashing. Empty path-list segments are harmless.

## Spec 30

The special compgen invocation `--argc-compgen SHELL ___compgen_kind___ KIND PARTIAL` completes built-in kinds. `shell` returns, in order, `bash, elvish, fish, nushell, powershell, xonsh, zsh, tcsh`. `path` lists files and directories, while `dir`/`folder` list directories only before shell-specific reduction. The exact direct kind `file` returns status 0 with empty stdout/stderr even when regular files or directories match; it does not act as an alias of `path`. This direct protocol also rejects suffix-bearing names: `file:.txt,.log` returns status 0 with empty stdout/stderr. The `file` and `file:.ext,...` forms remain usable as dynamic `__argc_value` directives under Spec 31 and through source value notations, rather than as productive direct special kinds. Generic built-in path completion does not expand directory entries: it emits exactly `__argc_value=path<TAB>/color:default`.

Path completion is relative to cwd unless input is absolute, `./`, nested, quoted, or begins `~`; preserve the corresponding filesystem prefix except for the literal `file:` scheme marker. For a `file://` partial, strip exactly `file:` from replacements while retaining the slashes: `file://./fi` completes as `//./file`, and `file:///absolute/path/fi` completes as `///absolute/path/file`. Retain filesystem directory-enumeration order rather than sorting entries lexically. In the observed fixture this makes Fish emit `dir1/`, `dir2/`, `file'with'quotes.txt`, `file1.txt`, `file2.txt`, `file with spaces.txt`, and `script.sh`, in that order. Append `/` to directory candidates and mark files as accepting a trailing space. Exclude hidden entries by default, follow valid symlinks, mark symlinked directories with `/`, and silently skip broken symlinks/unreadable/nonexistent directories. A leading-dot basename enables hidden matches for the direct `path` kind: with files `.hidden1` and `.hidden2`, Bash `path .h` emits `.hidden`; direct `file .h` is empty under the preceding direct-`file` rule. Dynamic file directives honor extension filters. For Bash direct `path`/`dir` completion, two or more matching directory candidates are reduced to their longer common prefix without an acceptance space: directories `subdir1/` and `subdir2/` produce only `subdir` for partial `""` or `s`. Matching regular files from direct `path` completion are not reduced this way: with `doc1.txt` and `doc2.txt`, partial `doc` emits the two exact lines `doc1.txt ` and `doc2.txt `, each including its trailing acceptance space. `<FILE>`, `<PATH>`, and `<DIR>` notations trigger their corresponding ordinary source-completion kinds even without a custom function.

## Spec 31

A dynamic completion function may emit ordinary lines `value`, `value<TAB>description`, or lines with directives. Shell-specific completion modes recognize:

- `__argc_prefix=P`: prepend `P` to emitted candidates while matching against the remaining user text;
- `__argc_suffix=S`: append `S`;
- `__argc_filter=F`: use `F` as the match prefix/filter;
- `__argc_cd=DIR`: resolve subsequent path completion relative to DIR;
- `__argc_value=path|file|dir|folder|arg|any|file:.ext,...`: switch to the named built-in value kind;
- `/color:NAME[,bold]` in a tab field: attach display color/style;
- a NUL immediately after a value: mark it “no trailing space”.

When a shell-specific mode interprets them, prefix/suffix combine and directive lines are not candidates. Apply suffixes to logical candidates before filtering/common-prefix reduction, and add the prefix only when serializing the replacement. Bash word-break processing can then remove a prefix segment: with `COMP_WORDBREAKS` containing `:`, an `http://` prefix yields bare `example.com` and `github.com` replacement lines. Generic mode does not interpret dynamic prefix/filter directive lines and serializes them as ordinary candidates. If `_prefix` prints `__argc_prefix=http://`, `__argc_filter=`, `example.com`, and `github.com`, generic completion emits those same four candidate values in that order, each followed by `<TAB>/color:default`; it does not prepend `http://` to the last two.

Descriptions may contain parentheses and Unicode. Before adding shell-specific description delimiters, trim surrounding whitespace/tabs and remove one pair of parentheses when they enclose the entire description. Description truncation is always active. With `ARGC_COMPGEN_DESCRIPTION_MAX_WIDTH` absent, retain the first 80 display columns and append `...`; when it is set to integer `N`, the observed cutoff retains `N + 3` display columns and then appends `...`. With the variable set to `7`, an empty partial for the `long-desc` dynamic positional emits the description `Short desc...` for candidate `--short`; as specified in Spec 29, partial `--s` emits no candidate at all. `NO_COLOR` suppresses color codes/styles without changing values/descriptions. `ARGC_COMPGEN_DESCRIPTION` controls whether descriptions are included where supported.

## Spec 32

Candidate serialization is shell-specific. Except for Bash's deliberate longest-common-prefix replacement, it preserves each logical candidate value:

- Bash: first compute the longest common prefix of logical values after filtering and after applying dynamic suffixes. If two or more values have a common prefix longer than the current filter (other than the special common value `--`), emit only `PREFIX + COMMON` with no description or acceptance space. Subject to the direct-filesystem exceptions in Spec 30, this applies across candidate families: `cmd1`/`cmd2` at filter `c` produce `cmd`; `filtered_value1`/`filtered_value2` produce `filtered_value`; dynamically suffixed `file1.txt`/`file2.txt` produce `file`; and a dynamic prefix plus `middle1_suffix`/`middle2_suffix` produces `prefix_middle`. Otherwise, with multiple matches, serialize a described candidate as `value (description)` with no trailing space and an undescribed candidate as `value` followed by a trailing literal acceptance space, except that candidates for a delimiter-bearing multi-value option are no-space candidates. Thus initial choices for `--language+,[python|rust|javascript|go]` are exactly four newline-terminated bare words with no trailing spaces. If filtering leaves exactly one candidate, suppress its description and emit the bare value followed by the acceptance space unless that candidate is explicitly no-space; this applies to declared flags/options, automatic `-h`, and `+`-prefixed symbols. Escape only characters required at their position. Respect `COMP_WORDBREAKS`: when `:`, `=`, or `@` is a word break, return only the segment Bash replaces; when absent, retain the complete value.
- Fish: `value<TAB>description`.
- Generic: `value<TAB>/color:COLOR<TAB>description`; built-in command candidates use magenta.
- Zsh: `value[space]<TAB>display:description<TAB>color-key<TAB>ANSI-color-number`; strip one pair of parentheses when they wrap the entire description. The space before the first tab is present for accepting candidates. Flags use ANSI `36`, value-taking options use `1;36`, and commands use `35`. For example, `--name` is exactly `--name <TAB>--name:Name parameter<TAB>--name<TAB>1;36`.
- PowerShell and Elvish: five tab-separated fields `value, append-space(0/1), display, description, color`; the second field is `1` when the candidate accepts a trailing space and `0` when it must not. PowerShell uses ANSI colors `36` for flags, `1;36` for value-taking options, and `35` for commands; Elvish uses `cyan`, `cyan bold`, and `magenta` respectively. Thus an ordinary `--verbose` flag is `--verbose<TAB>1<TAB>--verbose<TAB>Enable verbose output<TAB>36` for PowerShell and ends in `cyan` for Elvish, while `--name` ends in `1;36`/`cyan bold`. With colors enabled, a PowerShell path directory is exactly `dir1/<TAB>0<TAB>dir1/<TAB><TAB>1;34`; an ordinary file is `file1.txt<TAB>1<TAB>file1.txt<TAB><TAB>39`.
- Xonsh: four tab-separated fields `value, append-space, display, description`. The second field is `1` when the candidate accepts a trailing space and `0` when it does not. An ordinary described command is `cmd1<TAB>1<TAB>cmd1<TAB>First command`; pseudo-help is descriptionless and is exactly `help<TAB>1<TAB>help<TAB>`.
- Nushell: append a literal space only for an accepting candidate, then append `TAB + description` only when a nonempty description exists. Consequently, descriptionless path directories are bare `dir1/` lines, while files are `file1.txt ` with one trailing space and no tab.
- Tcsh: when two or more candidates remain, emit one per line with ASCII spaces replaced by U+2800 BRAILLE PATTERN BLANK and parenthesized descriptions. When exactly one remains, suppress its description and emit only the sanitized value; completing `cmd1` yields exactly `cmd1`.

For unbalanced leading quotes, remove the opening quote from replacement values and suppress acceptance spaces. In Bash, if several path matches have no common extension beyond the unquoted filter, prefix only the first emitted replacement with one literal ASCII space; for partial `"file` in the observed path fixture the first line is ` file'with'quotes.txt` and the later `file1.txt`, `file2.txt`, and `file with spaces.txt` lines have neither opening quote nor trailing space. Handle middle quotes and trailing backslashes with the same shell-specific escaping machinery, correctly escaping `$`, `!`, `#`, quotes, backslashes, commas, colons, equals signs, and `@` without double escaping.

## Spec 33

`--argc-parallel FILE JOB...` requires a script plus at least one job token; otherwise fail status 1 with `Usage: argc --argc-parallel <SCRIPT> <ARGS>...`. The script must contain an argc eval activation; otherwise fail with `Parallel only available for argc based scripts.`. A load failure uses `Failed to load script at 'PATH'` and its cause.

Split jobs at the exact token `:::`. Ignore empty groups caused by leading, repeated, or trailing separators. In each nonempty group, the first token selects the task function and every remaining token is forwarded directly to that Bash function as its raw `$@`; those tokens are not parsed against the command declaration and do not populate that command's declared `argc_*` positional variables. Thus `work x y` calls `work` with `$1=x` and `$2=y`, but declared `argc_a` and `argc_b` remain empty. A handler that reads only `$argc_label` therefore prints an empty label even though the group's label token is still present in its raw `$@`. The raw tokens are not checked against declared positional capacity, so a zero-positional function can receive `arg1 arg2 arg3`, and separate groups can receive different argument counts. Execute the groups concurrently, preserving every raw argument boundary and inherited environment. Export `ARGC_PARALLEL=1` in children and restore parent parser state from `ARGC_VARS`, so child tasks can read parent options. Capture each child's stdout and stderr separately, then concatenate each stream in original job order, not completion order. Do not stop after failure. Return 0 only if all jobs succeed; return 1 if any child has any nonzero status. Empty-output jobs contribute nothing.

## Spec 34

`--argc-script-path` performs the closest-parent search over the default recognized Argcfile names from Spec 2 and prints an absolute path. It ignores `ARGC_SCRIPT_NAME`: if the current directory contains `argcfile`, setting `ARGC_SCRIPT_NAME=missing` still succeeds and prints the absolute path to that `argcfile`. If no default-name file is found, fail status 1 with `Argcfile not found.`. Search does not require the file to be executable and must prefer a nearer file over a parent file.

`--argc-shell-path` first honors `ARGC_SHELL_PATH`; it checks existence but does not check execute permission. An existing non-executable file is accepted with status 0, its path on stdout, and empty stderr. A missing path fails status 1 with `Invalid ARGC_SHELL_PATH, 'PATH' does not exist`. Otherwise discover Bash deterministically via the environment/PATH and print its absolute canonical path; in the required Linux environment this is `/usr/bin/bash`.

## Spec 35

Specification-time duplicate checking is scope aware. Reject duplicate positional ids, environment ids, short names, long names, or a flag/option cross-kind spelling collision in the same command, and include both the new directive line and original line, for example `@option(line 4) has '-v' already exists at line 3`. The same option spelling may be reused independently in sibling commands. Duplicate checking uses declared ids/spellings, not their sanitized Bash-variable targets: distinct options such as `--foo-bar` and `--foo.bar` are both accepted even though both normalize to `argc_foo_bar`. Preserve names containing hyphen, dot, colon, or `@` in user-facing notation while normalizing only the shell variable.

Reject structurally impossible modifier combinations, missing required parent commands, invalid subcommand names, alias conflicts, and invalid metadata with a source-line diagnostic. Conversely, tolerate unrelated invalid Bash syntax during pure parsing/eval generation, tolerate a completely empty script, and tolerate recognized annotations without `@describe`; these still export/build into a minimal root with automatic controls.

## Spec 36

All modes must use the ordering, whitespace, quoting, and stream selection specified here because their textual forms are public interfaces. Utility failures (`build`, `export`, `mangen`, `create`, `run`, completion-script generation, path/shell discovery, parallel setup) use nonzero process status and stderr. Eval parsing/matching/specification failures use successful process status plus eval-safe stdout that exits when evaluated. Compgen discovery failures are silent successful empty results. Help and version requested through a source argc-based script are eval-safe snippets that print to stderr and exit 0; direct `--argc-help`/`--argc-version` and help/version executed by a standalone built script print to stdout.

The implementation must remain safe for arbitrary user values: generated Bash must never execute argument contents, completion must not interpret candidates as code, JSON must be valid, and all subprocess calls must preserve arguments rather than joining and reparsing them. File-producing modes must create only requested parent directories, preserve unrelated files, and never overwrite an existing Argcfile during create.
