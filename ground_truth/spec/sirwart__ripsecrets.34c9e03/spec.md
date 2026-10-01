# Clarified specification for `executable`

## Spec 1

The required artifact is one executable file named exactly `executable`. It implements the `ripsecrets` command-line interface. It has two mutually exclusive operating modes:

1. normal mode scans source files for secrets; and
2. `--install-pre-commit` mode installs a Git pre-commit hook.

The process exit statuses are part of the interface:

- `0`: a scan completed with no accepted secret matches, help/version was printed, or hook installation succeeded;
- `1`: a scan found one or more accepted secret matches; and
- `2`: command-line usage was invalid, a supplied regular expression could not be compiled, or hook installation failed.

Finding a secret is not an operational error: findings go to standard output and standard error stays empty. With a clean scan both streams are empty. File-walking errors are diagnostics but do not by themselves make a scan fail: a scan containing only missing paths exits `0`; a scan containing a missing path and a valid file with a secret reports the path error on standard error, reports the finding on standard output, and exits `1`.

## Spec 2

The supported arguments are:

- zero or more positional source paths;
- `--install-pre-commit`;
- `--strict-ignore`;
- `--only-matching`;
- repeatable `--additional-pattern <ADDITIONAL_PATTERNS>`;
- `-h` and `--help`; and
- `-V` and `--version`.

There are no `-o`, `-s`, `-a`, or combined-short-option aliases. Options may occur before or after positional paths. A standalone `--` ends option parsing, and every later token is a literal source path even when it starts with `-`. A literal `-` is a path-like argument and does not cause standard input to be scanned. An absent value after `--additional-pattern` is a parse error with exit `2` and standard error containing `a value is required for '--additional-pattern <ADDITIONAL_PATTERNS>'`. Unknown options exit `2`, write nothing to standard output, and use the form shown here (substitute the actual rejected option):

```text
error: unexpected argument '--invalid-flag' found

  tip: to pass '--invalid-flag' as a value, use '-- --invalid-flag'

Usage: executable [OPTIONS] [Source files]...

For more information, try '--help'.
```

For a combined token such as `-abc`, the rejected option named in the diagnostic is `-a`.

## Spec 3

`--version` and `-V` print exactly the following single newline-terminated line to standard output, print nothing to standard error, and exit `0`:

```text
ripsecrets 0.1.11
```

`-h` prints exactly this short help, including blank lines, spacing, punctuation, and its final newline:

```text
A command-line tool to prevent committing secret keys into your source code

Usage: executable [OPTIONS] [Source files]...

Arguments:
  [Source files]...  Source files. Can be files or directories. Defaults to '.'

Options:
      --install-pre-commit
          Install `ripsecrets` as a pre-commit hook automatically in git directory provided
      --strict-ignore
          If you pass a path as an argument that's ignored by .secretsignore it will be scanned by default. --strict-ignore will override this behavior and not search the paths passed as arguments that are excluded by the .secretsignore file. This is useful when invoking secrets as a pre-commit
      --only-matching
          Print only the matched (non-empty) parts of a matching line, with each such part on a separate output line
      --additional-pattern <ADDITIONAL_PATTERNS>
          Additional regex patterns used to find secrets. If there is a matching group in the regex the matched group will be tested for randomness before being reported as a secret
  -h, --help
          Print help (see more with '--help')
  -V, --version
          Print version
```

`--help` prints exactly this long help, also to standard output with empty standard error and exit `0`:

```text
ripsecrets searches files and directories recursively for secret API keys.
It's primarily designed to be used as a pre-commit to prevent committing
secrets into version control.

Usage: executable [OPTIONS] [Source files]...

Arguments:
  [Source files]...
          Source files. Can be files or directories. Defaults to '.'

Options:
      --install-pre-commit
          Install `ripsecrets` as a pre-commit hook automatically in git directory provided

      --strict-ignore
          If you pass a path as an argument that's ignored by .secretsignore it will be scanned by default. --strict-ignore will override this behavior and not search the paths passed as arguments that are excluded by the .secretsignore file. This is useful when invoking secrets as a pre-commit

      --only-matching
          Print only the matched (non-empty) parts of a matching line, with each such part on a separate output line

      --additional-pattern <ADDITIONAL_PATTERNS>
          Additional regex patterns used to find secrets. If there is a matching group in the regex the matched group will be tested for randomness before being reported as a secret

  -h, --help
          Print help (see a summary with '-h')

  -V, --version
          Print version
```

## Spec 4

In scan mode, no positional sources means the single source `.`. Each source may be a regular file or directory. Directories are traversed recursively without filtering by filename extension: ordinary text, JSON, source code, scripts, executable files, uppercase/double extensions, and files without extensions are all eligible. Empty files/directories and whitespace-only files are valid clean inputs. Recursion must handle at least 50 nested levels, hundreds of files, 10,000-line files, and lines tens of thousands of bytes long.

Multiple sources are all processed. Passing the same file directly and also through a directory is not deduplicated: it is scanned and reported twice. Preserve explicit-source order and increasing line order within a file. Directory traversal must be stable enough that repeated scans return the same findings.

Path text in output follows the spelling and kind of the traversed path rather than being canonicalized. An absolute source produces absolute result paths. A relative source produces relative paths, including a leading `./` and `..` components when supplied. Files discovered below a directory are printed by joining their relative descendant path to the supplied directory spelling. An explicitly passed symbolic link to a file is followed, but the printed path is the link path. An explicitly passed symbolic link to a directory is followed and descendant paths are printed below the link path.

Hidden paths encountered during ordinary recursive traversal, especially `.git`, are skipped by default. A hidden file explicitly named as a source is nevertheless scanned. Read-only and executable regular files are scanned normally. `/dev/null` is accepted as a clean source.

## Spec 5

Scanning is byte-oriented and line-oriented. Do not require valid UTF-8. A secret in an ASCII portion of a file is still found when other lines contain invalid UTF-8 or Latin-1 bytes. UTF-8 text, UTF-8 BOMs, non-ASCII text around a candidate, Unicode filenames, NUL bytes, and other control bytes must not crash the process. A NUL following a match may remain in the reported full line. A clearly binary file with no match is clean.

Only LF (`0x0A`) delimits input lines. Patterns never join content across an LF boundary. A CR (`0x0D`) is not a line boundary or a stripped terminator: CR-only content remains one line, and in CRLF content the CR remains part of the line payload. Both a final line without a trailing LF and a first or last line are scanned. Line numbers are one-based. For example, scanning `clean\rghp_AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA\r\nclean\ngho_BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB\rfinal` reports line 1 with payload `clean\rghp_AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA\r` and line 3 with payload `gho_BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB\rfinal`.

In output, omit the LF input terminator and end every result record with one `\n`; otherwise preserve the full original line bytes in default mode, including indentation, Unicode, long content, and control bytes. One exception is a UTF-8 BOM (`EF BB BF`) at the beginning of a file: it is stripped before matching and is absent from the first output payload. Thus a first line consisting of a BOM followed by two spaces, `☃ `, and a GitHub token is reported with the two spaces as the first payload bytes.

## Spec 6

Every accepted result record is written to standard output in this form:

```text
PATH:ONE_BASED_LINE_NUMBER:PAYLOAD\n
```

In default mode, `PAYLOAD` is the entire physical input line. A physical line with one or several accepted matches is printed once. Thus a line containing both a GitHub and GitLab token contains both in the one full-line record.

With `--only-matching`, `PAYLOAD` is only the accepted match span, and every match gets its own record. This includes zero-length matches produced by a custom pattern, whose payload is empty. Multiple accepted patterns or duplicate occurrences on one physical line therefore produce multiple records, all with the same path and line number. For example, these three assignment lines:

```text
secret_access_key = '1W0T1eqNpAk3imtH8mJtkSf2AQ3eNMrPqe3u3Tf6'
secretAccessKey = "wrmDCcpolP3yg9l7o9dJragXbj2wFFzWgiN5FBZN"
SECRET_ACCESS_KEY: 2OYzBCp/+N9pUJ3a8JA5lOLYL/iKBFYVlif3pIHl
```

produce only the respective 40-character values as payloads under `--only-matching`, while default mode prints all three complete assignment lines.

## Spec 7

Compile one byte-regex by wrapping all alternatives in one outer capturing group. The built-in alternatives, in exact priority order, are listed below. Use greedy, leftmost-first matching. Bracketed ASCII ranges have their literal ASCII meanings; `\d` means a digit, `\S` means a non-whitespace character, `\w` accepts Unicode word characters as well as ASCII letters/digits/underscore, `\b` is a word boundary, `(?i:...)` makes only its contents case-insensitive, `(?:...)` is noncapturing, and `$` matches the end of a searched line. The dialect has no lookaround or backreferences.

```text
[A-Za-z]+://\S{3,50}:(\S{8,50})@[\dA-Za-z#%&+./:=?_~-]+
\beyJ[\dA-Za-z=_-]+(?:\.[\dA-Za-z=_-]{3,}){1,4}
(?:gh[oprsu]|github_pat)_[\dA-Za-z_]{36}
glpat-[\dA-Za-z_=-]{20,22}
[rs]k_live_[\dA-Za-z]{24,247}
sq0i[a-z]{2}-[\dA-Za-z_-]{22,43}
sq0c[a-z]{2}-[\dA-Za-z_-]{40,50}
EAAA[\dA-Za-z+=-]{60}
AccountKey=[\d+/=A-Za-z]{88}
AIzaSy[\dA-Za-z_-]{33}
npm_[\dA-Za-z]{36}
//.+/:_authToken=[\dA-Za-z_-]+
xox[aboprs]-(?:\d+-)+[\da-z]+
<master>\{[\dA-Za-z]+\\}</master>
https://hooks\.slack\.com/services/T[\dA-Za-z_]+/B[\dA-Za-z_]+/[\dA-Za-z_]+
SG\.[\dA-Za-z_-]{22}\.[\dA-Za-z_-]{43}
(?:AC|SK)[\da-z]{32}
[\da-f]{32}-us\d{1,2}
s-s4t2(?:af|ud)-[\da-f]{64}
PuTTY-User-Key-File-2
AGE-SECRET-KEY-1[\dA-Z]{58}
-{5}BEGIN DSA PRIVATE KEY-{5}(?:$|[^-]{63,}-{5}END)
-{5}BEGIN EC PRIVATE KEY-{5}(?:$|[^-]{63,}-{5}END)
-{5}BEGIN OPENSSH PRIVATE KEY-{5}(?:$|[^-]{63,}-{5}END)
-{5}BEGIN PGP PRIVATE KEY BLOCK-{5}(?:$|[^-]{63,}-{5}END)
-{5}BEGIN PRIVATE KEY-{5}(?:$|[^-]{63,}-{5}END)
-{5}BEGIN RSA PRIVATE KEY-{5}(?:$|[^-]{63,}-{5}END)
-{5}BEGIN SSH2 ENCRYPTED PRIVATE KEY-{5}(?:$|[^-]{63,}-{5}END)
(?i:key|token|secret|password)\w*["']?]?\s*(?:[:=]|:=|=>|<-|>)\s*[\t "'`]?([\w+./=~\-\\`^]{15,90})(?:[\t\n "'`]|</|$)
```

After these alternatives, append every additional pattern in command-line order, then close the outer group. Built-ins are case-sensitive except for the four keywords inside `(?i:...)`. Do not require delimiters after fixed-length built-ins: for example, a GitHub token with more than 36 permitted body characters still matches its first 36 characters, though default output shows the whole containing line.

## Spec 8

The ordered regex recognizes, among other things, all of these tested families exactly according to the stated forms:

- URL credentials with an alphabetic scheme, 3–50 non-whitespace username characters, an 8–50 non-whitespace password, `@`, and the allowed host/path characters. The password capture, rather than the entire URL, is the candidate span.
- JWT/JWE-like values beginning with case-sensitive `eyJ`, followed by 1–4 dot segments of at least three base64url-like characters. Lowercase `eyj`, `EyJ`, bare `eyJ`, and matches split across lines are clean.
- GitHub `ghp_`, `gho_`, `ghs_`, `ghu_`, `ghr_`, and `github_pat_` bodies of 36 allowed characters; GitLab `glpat-` bodies of 20–22 allowed characters.
- Stripe `sk_live_` and `rk_live_`; Square `sq0i??-`, `sq0c??-`, and `EAAA`; Azure `AccountKey=`; Google `AIzaSy`; modern and legacy npm; Slack `xox...` and webhook URLs; SendGrid; Twilio `AC`/`SK`; Mailchimp; Intra42; Maven master passwords; PuTTY markers; age keys; and the listed private-key headers.

Matching is language-agnostic. Recognizable material is reported inside comments, quoted strings, JSON, YAML, XML, environment files, URLs, and executable scripts. No parser for those languages is applied. A private-key begin header is sufficient because its alternative permits end-of-line immediately after the header; an end marker is not required for detection.

AWS access-key IDs such as `AKIAN95B87AWHT6U0699` are detected through the generic keyword-assignment alternative when they occur after context such as `aws_access_key =`, `AWS key:`, or a JSON key. AWS secret access keys are likewise generic high-randomness assignments, not a separate prefix alternative.

## Spec 9

Captures control candidate extraction and randomness filtering. Ignore the combined regex's outer capture. If the chosen alternative has one or more participating capture groups, use the first participating group as the candidate span and require it to pass the randomness test in Spec 10. If it has no participating capture, use the full match and do not apply randomness filtering. Consequently:

- the URL alternative tests and returns its password capture;
- the final generic alternative tests and returns its assigned-value capture;
- a custom pattern such as `prefix-([A-Za-z0-9]+)-suffix` tests and returns the group;
- a custom pattern using only noncapturing groups is unfiltered and returns its full match; and
- in default output the full physical line is still printed regardless of the candidate span.

When a candidate fails randomness, continue searching after that candidate so later matches can still be found. Zero-length full matches from a custom alternative are not suppressed. In particular, `--additional-pattern '' --only-matching input` on the one-line ASCII file `ordinary text\n` exits `1`, writes no standard error, and emits exactly 13 `input:1:\n` records—one empty-payload record for each byte of text before the LF.

## Spec 10

The randomness predicate is byte-exact and is defined here so no external entropy library is needed. Let `s` be the captured bytes and `n` its byte length. Choose alphabet size `B=16` if `s` fully matches `[0-9a-fA-F]{16,}`, else `B=36` if it fully matches `[0-9A-Z]{16,}`, else `B=64`.

Define the inclusive one-sided binomial-tail function `tail(n,x,q)` as follows. If `x < n*q`, sum the binomial probability from `i=0` through `x`; otherwise sum it from `i=x` through `n`:

```text
tail(n,x,q) = sum choose(n,i) * q^i * (1-q)^(n-i)
```

Here `choose(n,i) = n! / ((n-i)! * i!)`, and the sum uses the range selected in the preceding sentence.

Let `D` be the number of distinct byte values in `s`. Let `S(n,k)` be the Stirling number of the second kind (`S(n,1)=S(n,n)=1` and `S(n,k)=S(n-1,k-1)+k*S(n-1,k)`). Define:

```text
p_distinct = (sum from k=1 through D of B*(B-1)*...*(B-k+1)*S(n,k)) / B^n
```

For a byte range `(lo,hi)`, count bytes `b` satisfying `lo <= b < hi`—the upper comparison is intentionally strict. For `B=16`, `p_class = tail(n,count('0','9'),10/16)`. For `B=36`, it is the minimum of `tail(n,count('0','9'),10/36)` and `tail(n,count('A','Z'),26/36)`. For `B=64`, it is the minimum of the analogous digit, uppercase, and lowercase tails with probabilities `10/64`, `26/64`, and `26/64`.

For `B=64` only, also count adjacent byte pairs in `s` which occur in the following comma-separated set; duplicate occurrences in `s` each count. Let `M` be that count and `K` the number of entries in the set. Then `p_bigrams = tail(n,M,K/(64*64))`. (The use of `n`, not `n-1`, in this tail is intentional.) For other bases, `p_bigrams=1`.

```text
er,te,an,en,ma,ke,10,at,/m,on,09,ti,al,io,.h,./,..,ra,ht,es,or,tm,pe,ml,re,in,3/,n3,0F,ok,ey,00,80,08,ss,07,15,81,F3,st,52,KE,To,01,it,2B,2C,/E,P_,EY,B7,se,73,de,VP,EV,to,od,B0,0E,nt,et,_P,A0,60,90,0A,ri,30,ar,C0,op,03,ec,ns,as,FF,F7,po,PK,la,.p,AE,62,me,F4,71,8E,yp,pa,50,qu,D7,7D,rs,ea,Y_,t_,ha,3B,c/,D2,ls,DE,pr,am,E0,oc,06,li,do,id,05,51,40,ED,_p,70,ed,04,02,t.,rd,mp,20,d_,co,ro,ex,11,ua,nd,0C,0D,D0,Eq,le,EF,wo,e_,e.,ct,0B,_c,Li,45,rT,pt,14,61,Th,56,sT,E6,DF,nT,16,85,em,BF,9E,ne,_s,25,91,78,57,BE,ta,ng,cl,_t,E1,1F,y_,xp,cr,4F,si,s_,E5,pl,AB,ge,7E,F8,35,E2,s.,CF,58,32,2F,E7,1B,ve,B1,3D,nc,Gr,EB,C6,77,64,sl,8A,6A,_k,79,C8,88,ce,Ex,5C,28,EA,A6,2A,Ke,A7,th,CA,ry,F0,B6,7/,D9,6B,4D,DA,3C,ue,n7,9C,.c,7B,72,ac,98,22,/o,va,2D,n.,_m,B8,A3,8D,n_,12,nE,ca,3A,is,AD,rt,r_,l-,_C,n1,_v,y.,yw,1/,ov,_n,_d,ut,no,ul,sa,CT,_K,SS,_e,F1,ty,ou,nG,tr,s/,il,na,iv,L_,AA,da,Ty,EC,ur,TX,xt,lu,No,r.,SL,Re,sw,_1,om,e/,Pa,xc,_g,_a,X_,/e,vi,ds,ai,==,ts,ni,mg,ic,o/,mt,gm,pk,d.,ch,/p,tu,sp,17,/c,ym,ot,ki,Te,FE,ub,nL,eL,.k,if,he,34,e-,23,ze,rE,iz,St,EE,-p,be,In,ER,67,13,yn,ig,ib,_f,.o,el,55,Un,21,fi,54,mo,mb,gi,_r,Qu,FD,-o,ie,fo,As,7F,48,41,/i,eS,ab,FB,1E,h_,ef,rr,rc,di,b.,ol,im,eg,ap,_l,Se,19,oS,ew,bs,Su,F5,Co,BC,ud,C1,r-,ia,_o,65,.r,sk,o_,ck,CD,Am,9F,un,fa,F6,5F,nk,lo,ev,/f,.t,sE,nO,a_,EN,E4,Di,AC,95,74,1_,1A,us,ly,ll,_b,SA,FC,69,5E,43,um,tT,OS,CE,87,7A,59,44,t-,bl,ad,Or,D5,A_,31,24,t/,ph,mm,f.,ag,RS,Of,It,FA,De,1D,/d,-k,lf,hr,gu,fy,D6,89,6F,4E,/k,w_,cu,br,TE,ST,R_,E8,/O
```

Set `p = p_distinct * p_class * p_bigrams`. Reject the candidate when `p < 0.00001`. After that, if the bytes contain no ASCII digit, reject it when `p < 0.0001`; otherwise accept it. This must accept the high-variety examples shown in Spec 6 and values such as `iftkeq2y4qj0nbt`, `2Tm6cdsRVBTL9hRCmR6MRDTpMLFS4I`, and long random hex strings. It must reject short values, repeated-character values, `hello_world`, `PROJECT_NAME_ALIAS`, and ordinary constant references.

## Spec 11

Each `--additional-pattern` value is a regular-expression alternative compiled together with the built-ins. The option is repeatable and every occurrence remains active. Matching is case-sensitive unless the applicable part of the pattern uses an inline modifier such as `(?i)`. Support escapes, character classes, `\d`, `\S`, bounded/open quantifiers, alternation, noncapturing groups, and inline flags as supported by the regex dialect in Spec 7. A scoped modifier affects only its group: in `(?i:id)=(?:[a-z]+)-\d{3,}`, only `id` is case-insensitive, while `[a-z]+` remains case-sensitive. Consequently that pattern does not match `id=AbC-12345`; when it and `Q{2,}[0-9]+|NEVER` are applied with `--only-matching` to `id=AbC-12345 other QQQ999 tail`, the sole output is `input:1:QQQ999\n`. Patterns operate within individual LF-delimited lines. Separate input lines with matches produce separate records at their correct line numbers.

A custom alternative without a capture reports every full match without entropy filtering, even a repetitive or zero-length match. A custom alternative with a capture follows Specs 9–10. For example `mypattern_(\S+)` detects `mypattern_wrmDCcpolP3yg9l7o9dJragXbj2wFFzWgiN5FBZN` but filters `mypattern_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa`; `MYTOKEN-\S+` reports `MYTOKEN-aaaaaaaaaaaa` because it has no capture. Spec 9 defines the observable behavior of an empty custom alternative.

An invalid combined pattern exits `2`, emits no findings, and writes a diagnostic beginning `Error: regex parse error:` and ending with the regex engine's specific cause. In particular, adding the pattern `(` must produce this exact diagnostic (the caret line contains four leading spaces):

```text
Error: regex parse error:
    ([A-Za-z]+://\S{3,50}:(\S{8,50})@[\dA-Za-z#%&+./:=?_~-]+|\beyJ[\dA-Za-z=_-]+(?:\.[\dA-Za-z=_-]{3,}){1,4}|(?:gh[oprsu]|github_pat)_[\dA-Za-z_]{36}|glpat-[\dA-Za-z_=-]{20,22}|[rs]k_live_[\dA-Za-z]{24,247}|sq0i[a-z]{2}-[\dA-Za-z_-]{22,43}|sq0c[a-z]{2}-[\dA-Za-z_-]{40,50}|EAAA[\dA-Za-z+=-]{60}|AccountKey=[\d+/=A-Za-z]{88}|AIzaSy[\dA-Za-z_-]{33}|npm_[\dA-Za-z]{36}|//.+/:_authToken=[\dA-Za-z_-]+|xox[aboprs]-(?:\d+-)+[\da-z]+|<master>\{[\dA-Za-z]+\\}</master>|https://hooks\.slack\.com/services/T[\dA-Za-z_]+/B[\dA-Za-z_]+/[\dA-Za-z_]+|SG\.[\dA-Za-z_-]{22}\.[\dA-Za-z_-]{43}|(?:AC|SK)[\da-z]{32}|[\da-f]{32}-us\d{1,2}|s-s4t2(?:af|ud)-[\da-f]{64}|PuTTY-User-Key-File-2|AGE-SECRET-KEY-1[\dA-Z]{58}|-{5}BEGIN DSA PRIVATE KEY-{5}(?:$|[^-]{63,}-{5}END)|-{5}BEGIN EC PRIVATE KEY-{5}(?:$|[^-]{63,}-{5}END)|-{5}BEGIN OPENSSH PRIVATE KEY-{5}(?:$|[^-]{63,}-{5}END)|-{5}BEGIN PGP PRIVATE KEY BLOCK-{5}(?:$|[^-]{63,}-{5}END)|-{5}BEGIN PRIVATE KEY-{5}(?:$|[^-]{63,}-{5}END)|-{5}BEGIN RSA PRIVATE KEY-{5}(?:$|[^-]{63,}-{5}END)|-{5}BEGIN SSH2 ENCRYPTED PRIVATE KEY-{5}(?:$|[^-]{63,}-{5}END)|(?i:key|token|secret|password)\w*["']?]?\s*(?:[:=]|:=|=>|<-|>)\s*[\t "'`]?([\w+./=~\-\\`^]{15,90})(?:[\t\n "'`]|</|$)|()
    ^
error: unclosed group
```

## Spec 12

A finding is suppressed when the exact lowercase byte phrase `pragma: allowlist secret` occurs later on the same physical line. It may be introduced by any comment syntax (`#`, `//`, or otherwise), because the scanner only searches bytes. The suppression extends from the phrase through that line ending and causes scanning to resume on the next line. The phrase is case-sensitive. It does not suppress secrets on other lines. Ordinary comments without this phrase are scanned normally.

## Spec 13

Read `.secretsignore` relative to the process's current working directory when it exists. It has two roles. Before a line exactly equal to `[secrets]` (with its following newline), lines are gitignore-style path patterns. After that marker, each nonempty line which does not begin with `#` is a literal secret value to suppress. Secret values are byte-exact, case-sensitive strings rather than regexes; all occurrences in all files are suppressed when the chosen candidate span equals one of them. Comments and blank lines have no effect. An empty, comment-only, patterns-only, secrets-only, or combined file is valid.

Path patterns support the tested gitignore forms: literal filenames/directories, directory names with or without trailing `/`, `*`, `**`, extension globs such as `*.log`, prefix globs such as `test_*`, nested forms such as `*/build/` and `src/temp/`, comments beginning with `#`, blank lines, and standard `!` negation. Matching is case-sensitive. Ignoring a directory ignores all descendants. Multiple patterns all apply. Only the single `.secretsignore` loaded from the process's current working directory supplies path patterns or literal-secret suppressions. A `.secretsignore` merely encountered below a supplied directory is not loaded and does not filter that directory's descendants. For example, scanning `project` when only `project/.secretsignore` contains `generated/` still reports secrets from both `project/generated/secret` and `project/src/secret` and exits `1`.

A malformed path glob in the working-directory `.secretsignore` is silently discarded; its parse error produces no diagnostic and scanning continues. In particular, with `.secretsignore` containing exactly `[\n` and `input` containing `ghp_AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA\n`, `executable input` exits `1`, writes `input:1:ghp_AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA\n` to standard output, and leaves standard error empty.

## Spec 14

Path-ignore precedence distinguishes discovered paths from explicit source roots:

- During a directory/default scan, path patterns from the `.secretsignore` in the process's current working directory exclude matching descendants. Nested `.secretsignore` files discovered by traversal are not consulted, as specified in Spec 13.
- By default, an explicitly supplied source overrides its own `.secretsignore` exclusion. For example, `executable ignored.txt` scans `ignored.txt` even if it is listed, and an explicitly supplied ignored directory is traversed. Ignore rules can still apply to descendants discovered below that root.
- With `--strict-ignore`, exclusions also apply to every explicit source. Check parent components as well as the final path: if an ancestor directory is ignored, an explicitly named descendant is ignored. This works for relative and absolute sources and for multiple sources. If all sources are removed, exit cleanly with no output.
- Literal secret suppression from `[secrets]` applies regardless of strict mode or whether the file was explicit.

Ordinary `.gitignore` filtering is repository-aware. When the walked source lies within a recognized Git repository, honor root and nested `.gitignore` rules, including extension and directory globs, and skip repository metadata such as `.git`. A standalone directory tree with no `.git` repository marker does not activate its `.gitignore` rules: a walk still reports files matched by `*.tmp`, `build/`, or a literal such as `ignored.txt`. Once the otherwise identical tree is initialized as a Git repository, those rules filter the walked files. Explicitly naming an ignored file still overrides this traversal filtering and scans the file.

## Spec 15

For a nonexistent source or broken symlink, write this style of diagnostic to standard error and continue:

```text
SOURCE_AS_SPELLED: No such file or directory (os error 2)
```

If no other source yields a finding, the status remains `0` and standard output remains empty. If another source yields findings, the status is `1`. The special literal source `-` is treated as an empty/literal path rather than standard input; it is ignored silently, exits `0` when it is the only source, and must not consume stdin. Invalid UTF-8, permission edge cases, special files, and binary bytes must be handled without an uncaught exception or hang.

## Spec 16

`--install-pre-commit` uses the positional paths as Git repository roots; with no paths it uses `.`. It may install into multiple roots in one invocation. Each root must contain `.git`, otherwise stop and exit `2` with empty standard output and:

```text
Error: .git directory not found
```

The exact hook command bytes are:

```text
ripsecrets --strict-ignore `git diff --cached --name-only --diff-filter=ACM`
```

followed by exactly one newline and no trailing spaces or extra blank line. The backticks and the flag order are required. A newly created hook has its owner-execute permission bit set. Successful installation produces no standard output or standard error.

Normally the destination is `.git/hooks/pre-commit`; the `.git/hooks` directory is expected to exist. If it is absent, installation exits `2` and reports a `No such file or directory` error. If `.git/pre-commit.d` already exists, use `.git/pre-commit.d/ripsecrets` instead of `.git/hooks/pre-commit`, with the same exact content and executable bit.

## Spec 17

If `.git/hooks/pre-commit` already exists and does not already contain the exact hook-command byte sequence from Spec 16, append that sequence without overwriting or rearranging any existing bytes. Preserve its shebang as the first line. The command follows the existing content directly; normal existing hooks end in a newline. If the relevant hook file already contains the exact sequence—or `.git/pre-commit.d/ripsecrets` already exists—exit `2`, leave it unchanged, and write:

```text
Error: pre-commit hook has already been installed
```

The scan-only flags are invalid in installation mode. These exact diagnostics go to standard error, with exit `2` and empty standard output:

```text
Error: --strict-ignore is not a valid option when installing pre-commits. Use --install-pre-commit alone
```

```text
Error: --only-matching is not a valid option when installing pre-commits. Use --install-pre-commit alone
```

If both are supplied, report `--strict-ignore`. An additional-pattern option is not one of these two prohibited flags, though installation does not scan content.

## Spec 18

The installed command is deliberately executable by a shell as a Git hook. The harness provides `ripsecrets` on `PATH`; the `executable` artifact only has to write the command, not provide or emulate Git itself. On a commit, the command receives all staged added/copied/modified paths from `git diff --cached --name-only --diff-filter=ACM`, scans them with strict ignore behavior, and propagates the scanner status. Therefore a clean staged set permits the commit, while any detected secret blocks it with status `1`. Git forwards the hook's normal finding output to the commit's standard error; for example a staged file containing `aws_key = "AKIAN95B87AWHT6U0699"` produces:

```text
config.py:1:aws_key = "AKIAN95B87AWHT6U0699"
```

Nested staged paths are handled as ordinary relative paths. Multiple secret-bearing staged lines are all reported, while a mixture of clean and secret-bearing files is blocked because of the findings.
