# Clarified specification for `executable`

## Spec 1

The required artifact is a runnable file named exactly `executable`. It is a command-line real-number calculator with two modes:

- If one positional `INPUT` expression is supplied, it runs in command mode, evaluates that expression once, prints one result, and exits.
- If no positional expression is supplied, it runs a line-oriented REPL until end-of-file. When attached to a terminal it displays a `> ` prompt; when standard input is a pipe, it emits results without prompts.

A successful command-mode calculation exits 0, writes exactly the formatted result followed by `\n` to standard output, and writes nothing to standard error. An expression/evaluation failure in command mode exits 1, writes nothing to standard output, and writes one diagnostic ending in `\n` to standard error. Command-line argument errors exit 2, write nothing to standard output, and write their diagnostic to standard error. The REPL itself exits 0 at EOF and continues after individual expression errors.

## Spec 2

The command-line syntax is:

```text
executable [OPTIONS] [INPUT]
```

It supports these options, all case-sensitive:

- `-f FIX`, `-fFIX`, `--fix FIX`, and `--fix=FIX`: decimal precision, default 10, parsed as an unsigned decimal integer in the inclusive range 1 through 64.
- `-b RADIX`, `-bRADIX`, `--base RADIX`, and `--base=RADIX`: output radix, default 10, parsed as an unsigned decimal integer in the inclusive range 1 through 36. The tested useful conversions use bases 2 through 36.
- `-a UNIT`, `-aUNIT`, `--angle_unit UNIT`, and `--angle_unit=UNIT`: forward-trigonometry input unit, default `degree`. The only values are exactly `degree`, `radian`, and `gradian`.
- `-h` or `--help`: print command-line help.
- `-V` or `--version`: print version information.

Options may occur before or after `INPUT`. Each of `fix`, `base`, and `angle_unit` may occur at most once, including mixtures of its short and long forms. At most one positional expression is allowed. `--` ends option parsing, which is necessary to pass an expression beginning with `-`; for example, `executable -- -1` calculates negative one. Without `--`, a leading-dash expression such as `-5` is treated as an option error. Value-taking short options cannot be bundled: `-fb` is parsed as `-f b` and consequently fails integer validation.

After `--`, a token that resembles an option is evaluated as the positional expression, including its leading hyphens. In particular, `executable -- --help` does not invoke command-line help: it exits 1, writes nothing to standard output, and writes exactly `Parser Error: Too many operators, too few operands\n` to standard error.

## Spec 3

`executable --version` prints exactly:

```text
eva 0.3.1
```

and exits 0 with empty standard error. `-V` provides the same version facility.

`executable --help` exits 0 with empty standard error and prints exactly the following plain-text content, with the displayed blank lines, two-space option indentation, and a final newline:

```text
Calculator REPL similar to bc(1)

Usage: executable [OPTIONS] [INPUT]

Arguments:
  [INPUT]  Optional expression string to run eva in command mode

Options:
  -f, --fix <FIX>                Number of decimal places in output (1 - 64) [default: 10]
  -b, --base <RADIX>             Radix of calculation output (1 - 36) [default: 10]
  -a, --angle_unit <angle_unit>  Angle unit [default: degree] [possible values: degree, radian, gradian]
  -h, --help                     Print help
  -V, --version                  Print version
```

`-h` prints this same documented help. Help takes precedence over other arguments: both `--help --version` and `--help --definitely-not-a-real-flag` print help successfully rather than reporting another argument.

## Spec 4

Command-line diagnostics follow these exact layouts. The spelling, capitalization, quoting, blank lines, and final newline are significant.

An unknown option is:

```text
error: unexpected argument '--unknown-flag' found

  tip: to pass '--unknown-flag' as a value, use '-- --unknown-flag'

Usage: executable [OPTIONS] [INPUT]

For more information, try '--help'.
```

Substitute the actual option in both quoted positions (for example `--nonexistent` or `-1`). An unexpected second positional has the same first line and usage/footer, but no `tip` paragraph; for `executable 2+2 3+3`, its first line is `error: unexpected argument '3+3' found`.

A missing value is:

```text
error: a value is required for '--fix <FIX>' but none was supplied

For more information, try '--help'.
```

Use `--base <RADIX>` for base. For angle units, use `--angle_unit <angle_unit>` and insert this indented line immediately after the first line:

```text
  [possible values: degree, radian, gradian]
```

An invalid numeric type uses, for example:

```text
error: invalid value 'abc' for '--fix <FIX>': invalid digit found in string

For more information, try '--help'.
```

The same template applies to decimal-looking option values such as `3.5`, and base uses `--base <RADIX>`. A range failure instead ends its first line with `: VALUE is not in 1..=64` for fix or `: VALUE is not in 1..=36` for base. Thus 0, 65, and 1000 fail for fix; 0, 37, and 100 fail for base.

An invalid angle unit is:

```text
error: invalid value 'invalid' for '--angle_unit <angle_unit>'
  [possible values: degree, radian, gradian]

For more information, try '--help'.
```

Use the actual value, so uppercase `DEGREE` also fails. A duplicate value-taking option says `error: the argument '--fix <FIX>' cannot be used multiple times`, then a blank line, the usage line, another blank line, and the standard `For more information` footer. Substitute the corresponding canonical base or angle-unit option name.

## Spec 5

Expressions use IEEE-754 binary64 real arithmetic. Numeric literals are ordinary non-scientific decimal literals: integers, `12.34`, a leading-point form such as `.5`, and a trailing-point form such as `5.` are valid. Leading zeroes are valid. Spaces may appear around or between tokens and are ignored. Examples of literal behavior under default formatting are `.5` -> `0.5000000000`, `5.` -> `5.0000000000`, `0.0001` -> `0.0001000000`, and `999999999999999` -> `999,999,999,999,999.0000000000`.

The only constants are lowercase `pi` and `e`, with binary64 values equivalent to `3.141592653589793` and `2.718281828459045`. They are case-sensitive. The exact input `PI` exits 1, writes nothing to standard output, and writes `Parser Error: Too many operators, too few operands\n` to standard error. At default precision, `pi` prints `3.1415926536`, `e` prints `2.7182818285`, `pi+e` prints `5.8598744820`, and `pi*5^2` prints `78.5398163397`.

An underscore `_` is the REPL previous-answer token described later; it is not a general identifier. Arbitrary identifiers and Unicode/special tokens are not accepted.

## Spec 6

The expression operators are:

- Postfix factorial: `!`.
- Exponentiation: `^` and `**`, which are interchangeable and right-associative.
- Unary prefix `+` and `-`.
- Multiplication, division, and remainder: `*`, `/`, `%`, evaluated left-to-right.
- Addition and subtraction: `+`, `-`, evaluated left-to-right.

Parentheses group expressions and override precedence. Exponentiation binds more tightly than multiplication: `2^3*4` is 32 and `2*3^2` is 18. Power chains associate right: `2^3^2` and `2**3**2` are 512, while `(2^3)^2` is 64; `2^2^2^2` is 65,536. Unary signs are permitted after binary operators, so `5+-3` is 2, `5++3` is 8, `5--3` is 8, and `2^-1` is 0.5. Subtraction and division chains associate left: `10-5-2` is 3 and `20/4/2` is 2.5.

All operators can be mixed and nested. Representative default outputs are `2+3*4` -> `14.0000000000`, `(2+3)*4` -> `20.0000000000`, `10%3` -> `1.0000000000`, `5.5%2` -> `1.5000000000`, and `0^0` -> `1.0000000000`.

For the required unary/factorial interaction, a sign is part of the operand to which a following factorial is applied: `-1!` attempts factorial of -1 and therefore produces a domain error, just like `(-1)!`. A unary sign is also allowed as the right operand of exponentiation, as shown by `2^-1`.

## Spec 7

Implicit multiplication is inserted for adjacent value-producing constructs. Required forms include:

- number followed by an opening parenthesis: `2(3+4)` = 14;
- closing parenthesis followed by opening parenthesis: `(2)(3)` = 6 and `(2)(3)(4)` = 24;
- number followed by a function call: `3sin(30)` = 1.5;
- number and constant adjacency: `2pi` = 2*pi and `5pi` = 5*pi;
- constant followed by number: `pi2` = pi*2 and `e2` = e*2, not scientific notation;
- longer adjacency: `2pi3` = 2*pi*3;
- nested adjacency: `12sin(45(2))` = 12*sin(45*2) = 12 in default degree mode;
- in the REPL, a number followed by `_`: after evaluating 5, `2_` evaluates to 10.

Known function names are an exception: a function must have parentheses, so `sin2`, `cos3`, `sin_`, and `sin 30` do not mean multiplication and fail with `Syntax Error: Function 'NAME' expected parentheses`. The sequence `pi_` is also invalid and reports `Syntax Error: Unexpected character 'pi'`.

## Spec 8

Missing closing parentheses are automatically appended when the nesting is otherwise structurally valid. For example, `(2+3`, `((1+2)*(3+4`, `sin(30)+tan(45`, and `ceil(sqrt(3^2+5^2` evaluate as if enough `)` characters were appended, producing 5, 21, 1.5, and 6 respectively. Extra closing parentheses are never removed and cause `Syntax Error: Mismatched parentheses!`.

Functions require an immediately following parenthesized argument list. One-argument functions require exactly one expression; `log` and `nroot` require exactly two comma-separated expressions. Arguments may themselves be full nested expressions. A missing required argument reports `Parser Error: To few arguments for function, need N` (the word is intentionally spelled `To`), while too many arguments such as `nroot(23,3,4)` report `Parser Error: Too many operators, too few operands`. A doubled comma such as `log(5,,2)` reports `Syntax Error: Empty argument`. Commas outside a valid two-argument function context are errors. Specifically, `(1+1,2+2)` exits 1, writes nothing to standard output, and writes `Parser Error: Too many operators, too few operands\n` to standard error.

A syntactically supplied negative second argument has a reference-specific parsing outcome: `log(8,-2)` exits 1, writes nothing to standard output, and writes `Parser Error: To few arguments for function, need 2\n` to standard error. It does not reach logarithm domain evaluation.

## Spec 9

The supported one-argument functions and their real-number meanings are:

- `sin`, `cos`, `tan`: forward trigonometric functions, with input conversion controlled by the angle-unit option.
- `csc(x)=1/sin(x)`, `sec(x)=1/cos(x)`, and `cot(x)=1/tan(x)` with the same input conversion.
- `asin`, `acos`, `atan`, plus `acsc(x)=asin(1/x)`, `asec(x)=acos(1/x)`, and `acot(x)=atan(1/x)`. Their results are radians regardless of selected angle unit.
- `sinh`, `cosh`, `tanh`: ordinary hyperbolic functions with no angle conversion.
- `ln`, `log2`, `log10`.
- `sqrt`, `ceil`, `floor`, `round`, `abs`, `exp`, and `exp2`.
- `rad`, converting degrees to radians as `x*pi/180`, and `deg`, converting radians to degrees as `x*180/pi`.

The two-argument functions are `log(x, base)=ln(x)/ln(base)` and `nroot(x,n)=x^(1/n)` using binary64 operations.

Representative exact default outputs include:

```text
sqrt(2)             1.4142135624
sinh(1)             1.1752011936
cosh(1)             1.5430806348
tanh(1)             0.7615941560
exp(3)             20.0855369232
exp2(8)           256.0000000000
log(8,2)            3.0000000000
nroot(27,3)         3.0000000000
rad(180)             3.1415926536
deg(pi)            180.0000000000
```

Nested calls and expression arguments are required. For example, `exp(ln(5))` is 5, `floor(sqrt(3^2+5^2))` is 5, `log(1+(2^16),4)` prints `8.0000110068`, and `nroot(2+2,4+e^2)` prints `1.1294396449`.

## Spec 10

Forward trigonometry defaults to degree mode. Degree input is converted with `x*pi/180`; consequently `sin(30)=0.5000000000`, `sin(90)=1.0000000000`, `cos(60)=0.5000000000`, `tan(45)=1.0000000000`, `csc(30)=2.0000000000`, `sec(60)=2.0000000000`, and `cot(45)=1.0000000000`.

In `radian` mode, the input is used directly, so `sin(pi/2)=1.0000000000`, `cos(pi)=-1.0000000000`, and `tan(pi/4)=1.0000000000`.

For compatibility, tested `gradian` mode follows the calculator's observed conversion behavior and treats its numeric input like degree mode, rather than multiplying by pi/200. In particular, `--angle_unit gradian 'sin(100)'` prints `0.9848077530`.

Inverse trigonometric output remains radians in every mode: `asin(0.5)=0.5235987756`, `acos(0.5)=1.0471975512`, `atan(1)=0.7853981634`, `acsc(2)=0.5235987756`, `asec(2)=1.0471975512`, and `acot(1)=0.7853981634`. Wrapping these in `deg`, such as `deg(asin(1))`, produces degrees (`90.0000000000`).

## Spec 11

Factorial is a repeatable postfix operation over nonnegative integer-valued binary64 operands. Evaluate each factorial by starting with a binary64 accumulator of 1 and multiplying it by each consecutive integer from 1 through the operand in ascending order, with binary64 rounding after every multiplication. `0!` is 1, `5!` and `(2+3)!` are 120, `20!` prints `2,432,902,008,176,640,000.0000000000`, and `21!` prints `51,090,942,171,709,440,000.0000000000`. Repetition applies that same procedure to the previous binary64 result: `3!!` is 720 and `5!!` is 120 factorial. At default precision, `5!!` prints exactly:

```text
6,689,502,913,449,123,933,681,342,530,579,439,120,523,775,756,341,546,089,360,093,784,620,090,324,126,011,858,610,763,674,005,344,861,930,779,387,322,735,825,049,576,193,801,545,269,664,994,272,835,560,837,966,773,424,760,538,449,951,889,918,907,707,412,713,570,304.0000000000
```

A negative or non-integral operand produces the domain error described below.

The `round` function uses half-away-from-zero behavior: `round(0.5)=1`, `round(3.5)=4`, and `round(-2.5)=-3`; values below the half threshold round normally (`round(2.4)=2`). `ceil` is toward positive infinity and `floor` toward negative infinity, so `ceil(-3.2)=-3` and `floor(-3.8)=-4`.

## Spec 12

Every arithmetic operator result must be finite. Division by an evaluated zero divisor is a distinct failure and prints exactly:

```text
Math Error: Divide by zero error!
```

This applies inside larger expressions and function arguments. Remainder by zero follows a different reference behavior: it is treated as a non-finite operator result and therefore produces the too-large error below.

Any other operator or factorial result that is non-finite produces exactly this line (followed by a newline):

```text
Error: to large to process! Max value: 179769313486231570000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000
```

The typo `to large` is required. Examples that take this path include `5%0`, `10^1000`, `2^10000`, `10^500*10^500`, `171!`, `200!`, and `1000!`. Large but finite values remain successful: `2^1000`, `exp(700)`, and `120!` are printable.

## Spec 13

A function call whose binary64 result is NaN or infinite, or whose input is outside the supported real domain, exits 1 with exactly:

```text
Domain Error: Out of bounds!
```

This includes negative square roots; `ln`, `log2`, or `log10` of zero or a negative number; invalid `log` arguments or bases that reach function evaluation; `asin`/`acos` outside [-1,1]; negative `nroot` radicands under this calculator's binary64 `pow` behavior (even `nroot(-8,3)` is rejected); negative/non-integral factorials; and overflow inside functions such as `exp(1000)`. Domain checks apply equally when the bad call is nested in a larger expression. The negative-second-argument `log(8,-2)` case is the parser failure specified in Spec 8, not a domain error.

## Spec 14

Other expression syntax failures use these exact diagnostics and exit 1:

- Invalid token `@`: `Syntax Error: Unexpected token: '@'`
- Unknown called function `foo(2)`: `Syntax Error: Unknown function 'foo'`
- Invalid identifier `abc1`: `Syntax Error: Unexpected character 'abc1'`
- A known function without parentheses: `Syntax Error: Function 'sin' expected parentheses` (substitute the name).
- An incomplete prefix of a known function can instead leave an operator without an operand: `1 + co` reports `Parser Error: Too many operators, too few operands`.
- Extra/misplaced parentheses: `Syntax Error: Mismatched parentheses!`
- Empty comma-delimited argument: `Syntax Error: Empty argument`
- A bare operator, a trailing operator, insufficient operands, or excess operands/operators: `Parser Error: Too many operators, too few operands`
- `_` before any successful REPL result: `Syntax Error: No previous answer!`

For example, `+`, `2+`, `1+2*`, and `* 1+2` use the same parser error. Invalid input must not crash or hang.

## Spec 15

For radix 10, format a finite binary64 result in fixed-point notation with exactly `FIX` digits after the decimal point (default 10), never scientific notation. Preserve trailing zeroes and insert ASCII commas every three digits in the integer part. Normalize negative zero to positive zero. Formatting performs normal fixed-precision rounding on the binary64 value. Required examples are:

```text
1/3, default       0.3333333333
1/3, --fix 2       0.33
2/3, --fix 3       0.667
1/2, --fix 5       0.50000
0.000001, --fix 2  0.00
999.999, --fix 1   1,000.0
1234567.89          1,234,567.8899999999
1000000             1,000,000.0000000000
```

Precision beyond binary64's significant digits exposes its stored approximation and pads the remainder with zeroes. Required conformance values include:

```text
1/3, --fix 20  0.33333333333333331483
1/3, --fix 64  0.3333333333333333148296162562473909929394721984863281250000000000
1/7, --fix 20  0.14285714285714284921
pi, --fix 30   3.141592653589793115997963468544
e, --fix 25    2.7182818284590450907955983
```

## Spec 16

For output bases other than 10, use uppercase digits `0`-`9`,`A`-`Z`. First round the numeric result to `FIX` decimal places, then convert its integer and fractional parts to the requested radix. Generate fractional radix digits by repeated multiplication, up to `FIX` digits, and stop early once the fraction becomes zero; unlike radix 10, do not retain trailing fractional zeroes. Emit `.0` when the converted value is integral. Preserve a leading minus sign.

The non-decimal integer field has a reference-specific layout: left-pad the signed integer digit string with spaces to a minimum width of 10 characters, then insert commas every three characters from the right, including through that padding. This yields these exact complete output lines:

```text
--base 16 255       " ,   ,   , FF.0\n"
--base 2 15         " ,   ,  1,111.0\n"
--base 16 4095      " ,   ,   ,FFF.0\n"
--base 16 0-255     " ,   ,   ,-FF.0\n"
--base 2 1024       "10,000,000,000.0\n"
--base 36 1000      " ,   ,   , RS.0\n"
```

Conversion examples after ignoring padding and commas are: decimal 255 -> `377.0` in base 8; 256 -> `100.0` in base 16; 10 -> `101.0` in base 3; 25 -> `100.0` in base 5; 100 -> `3M.0` in base 26; 0.5 -> `0.1` in base 2; 0.125 -> `0.1` in base 8; 0.25 -> `0.4` in base 16; and 15.9375 -> `F.F` in base 16. Because decimal rounding occurs before conversion, `--fix 1 --base 16 '1/3'` produces padded `0.4`. Supplying a larger fix does not add radix trailing zeroes: binary 0.5 remains `0.1` even with `--fix 10`.

## Spec 17

The expression `help` is a special calculator command rather than command-line help. In command mode it exits 1, writes nothing to standard output, and writes a multi-line reference summary to standard error. In the REPL it is informational: print the summary to standard output, continue the REPL, and eventually exit 0. Numeric formatting flags do not alter this summary.

The summary must contain headings `Constants`, `Functions`, and `Operators`; list both constants `pi` and `e`; list every function

```text
deg tan sinh abs rad sin floor cot exp ceil sqrt log sec asin acsc exp2 asec tanh log10 acot round log2 acos csc ln nroot atan cos cosh
```

and list the operator symbols `- + / % * ^ !`. Items may be arranged in whitespace-separated columns and their ordering is not significant. Each heading is on its own line, sections are separated by blank lines, and the output ends with a newline.

## Spec 18

In a terminal REPL, initially display `> `, read one line, display either its formatted result or diagnostic, then display another `> `. Results already shown remain on screen. For example a session entering `2+2` and then `3*3` appears as:

```text
> 2+2
4.0000000000
> 3*3
9.0000000000
>
```

Terminal echo supplies the entered text; the executable supplies the prompts and result/error lines. EOF ends cleanly. When input is piped, process each line in sequence with no prompt and print each result on its own line. A blank line following a successful calculation is evaluated as zero under the default format; for input `5 + 3\n\n`, the two output lines are `8.0000000000` and `0.0000000000`.

The REPL keeps the last successful numeric result as `_` and replaces it after every later successful numeric evaluation. Thus the lines `5*5`, `_ + 10`, `_*2` produce 25, 35, and 70. Zero is a valid previous value. An error does not terminate the loop: after `1/0`, a subsequent `2+2` still produces 4. REPL expression diagnostics are displayed in the REPL output rather than causing the whole process to exit 1.

REPL input history persists across invocations for the same user home. If no history can be loaded for a newly isolated home, print the exact line `No previous history.` to standard output before processing input. Save submitted history so a later invocation with that same home no longer prints that line. Command mode does not show REPL prompts or this history notice.
