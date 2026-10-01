# Executable behavioral specification

The required artifact is a command-line program named exactly `executable`. In the syntax below, `executable` is followed by a subcommand and its arguments. Unless a command explicitly says otherwise, successful processing exits with status 0, writes its data to standard output, and writes no diagnostic. Decimal integers and floating-point options use ordinary base-10 syntax.

## Spec 1

With no command, print a usage summary to standard error and exit 1. It must contain `Usage:`, `seqtk <command>`, `Version: 1.5-r133`, and at least the command names `seq`, `size`, `comp`, `sample`, `subseq`, `fqchk`, and `trimfq`. The implemented command set is:

`seq`, `size`, `comp`, `sample`, `subseq`, `fqchk`, `trimfq`, `mergepe`, `dropse`, `mergefa`, `famask`, `mutfa`, `split`, `rename`, `randbase`, `cutN`, `gap`, `listhet`, `hety`, `gc`, `hpc`, `hrun`, `kfreq`, and `telo`.

Any other first argument, including `--help`, exits 1 and writes `[main] unrecognized command 'ARG'. Abort!` to standard error (with a trailing newline). A subcommand that requires arguments exits 1 and prints a `Usage:` line naming that subcommand when those arguments are absent. An input path that cannot be opened normally exits 1 with a standard-error message containing `[E::stk_COMMAND] failed to open the input file/stream.`; `subseq` omits the final period for its sequence-input error.

## Spec 2

Sequence inputs are FASTA or FASTQ. Parse a header marker (`>` or `@`), then a name ending at the first whitespace, and retain the rest of that header as its comment. Concatenate multiline sequence data. For FASTQ, read sequence data through the `+` separator and then the same number of quality characters; emitted FASTQ always uses a bare `+` line. Empty files are valid. Commands must handle multiple records and zero-length records as specified below.

A filename `-` means standard input. `seq`, `size`, `rename`, `hpc`, and `telo` also use standard input when their filename is omitted in a noninteractive invocation; other commands enforce their stated positional arguments. Regular inputs may be uncompressed or gzip-compressed, regardless of suffix. Sequence names, comments, bases, and qualities are otherwise byte-preserving and case-preserving.

The common record serializer emits `@name[ comment]` when a nonempty quality string is present and `>name[ comment]` otherwise. It emits sequence and quality at the selected wrap width, with a newline after every record component. A width of zero means one unwrapped line, not an empty line per base. Unless another width is stated, output sequences and qualities are each one line.

## Spec 3

`executable seq [options] [input]` performs general transformations. It passes FASTA and FASTQ through in normalized record formatting by default. It accepts both separated options (`-l 10`) and attached options (`-l10`, `-s100`). These selection options are required:

- `-L N`: discard records whose original sequence length is less than `N`; equality is retained.
- `-f F`: independently retain a record when the command's pseudorandom draw is less than `F`. `F=1` retains all and `F=0` retains none. `-s N` selects the seed, default 11.
- `-1` retains input records numbered 1, 3, 5, ...; `-2` retains 2, 4, 6, ... . Numbering is the original input record number.
- `-N`: discard any resulting record containing a base other than case-insensitive A, C, G, or T.

The processing order is length test, random test, odd/even test, transformations, and finally the `-N` ambiguity test. Thus filtered-out short records consume neither a random draw nor a different input record number. `-l N` sets the sequence and quality wrap width; `-l 0` is unwrapped. `-C` removes the header comment but retains the name. `-a` and `-A` are aliases that discard quality and force FASTA.

## Spec 4

The `seq` base/quality transforms occur in this order:

1. `-S` removes whitespace positions from the sequence and the corresponding positions from quality.
2. `-q N` masks positions whose raw quality byte is strictly less than `N + Q`, where `Q` is set by `-Q` and defaults to 33. Without `-n`, masking lowercases the existing base; with `-n C`, it replaces the base by the first byte of `C`. A threshold of zero disables this quality masking.
3. `-U` uppercases every base. Otherwise, `-x -n C` replaces every lowercase base with `C`. Consequently `-U` takes precedence over `-x`.
4. `-a`/`-A` discards quality. Otherwise `-F C`, for a quality byte from ASCII 33 through 127, creates or replaces the quality string with `C` repeated to sequence length, producing FASTQ from FASTA.
5. `-C`, region masking, and strand operations follow as described in later sections.
6. `-V`, when used with nondefault `-Q Q`, subtracts `Q-33` from every output quality byte. For example, `seq -V -Q 64` maps `IIII` to `****`. Without `-V`, `-Q` affects threshold interpretation but not emitted qualities.

Quality comparison is strict: a base exactly at the low threshold is not masked. For example, with `-q 40` and default offset 33, quality `I` (ASCII 73) is retained while `H`, `G`, and `F` mask. With no `-n`, `ATCGATCGATCG` paired to `IIIHHHGGGFFF` becomes `ATCgatcgatcg`; with `-n N`, it becomes `ATCNNNNNNNNN`.

Preserve this observable `-S` compatibility quirk in unwrapped output: compaction shifts the nonwhitespace sequence bytes, and their corresponding quality bytes, to the left in their existing buffers, but it does not reduce the stored sequence or quality lengths before the common unwrapped serializer runs. Bytes remaining in the old buffer tail are therefore also emitted. Thus a record whose sequence is `ATCG ACGT` and quality is `IIII IIII` emits sequence `ATCGACGTT` and nine `I` quality characters. This behavior is required.

## Spec 5

`seq -M regions [ -c ] [ -n C ]` masks by a tab/whitespace-delimited region file. Each row starts with a sequence name. A three-column row gives a zero-based, half-open `[start,end)` interval. A name alone denotes the entire sequence. Multiple rows for a name all apply independently, and ends beyond sequence length are clamped. Names not present in the sequence input have no effect.

Normally bases inside listed intervals are lowercased, or replaced by `C` when `-n C` is present. With `-c`, mask their complement instead. If `-c` is used and a sequence has no region rows, mask that whole sequence. Coordinates refer to the original orientation and masking happens before reverse complementation. Qualities are not masked.

For example, masking `[2,5)` in `ATCGATCG` gives `ATcgaTCG`; complement masking gives `atCGAtcg`. With `-n N`, ordinary masking gives `ATNNNTCG`.

## Spec 6

`seq -r` reverse-complements every selected sequence and reverses its quality string. `seq -R` first emits the transformed forward record with `+` appended directly to its name, then emits the reverse-complement record with `-` appended. Header comments follow the suffixed name. `-R -a` emits the two records as FASTA. Base/quality masking and BED masking occur before the strand operation.

Complement while preserving case using A↔T, C↔G, R↔Y, M↔K, B↔V, D↔H; S, W, and N complement to themselves. Other ordinary bytes remain as defined by the same case-preserving mapping, including X→X. For example, `ATCGRYSWKMBDHVN` reverse-complements to `NBDHVKMWSRYCGAT`.

## Spec 7

All seeded sampling in `seq` and `sample` uses the same MT19937-64 generator. This is part of the output contract. Initialize 312 64-bit words by `mt[0]=seed` and, for `i=1..311`, `mt[i]=(6364136223846793005 * (mt[i-1] xor (mt[i-1]>>62)) + i) mod 2^64`. On exhaustion, twist with `NN=312`, `MM=156`, upper mask `UM=0xffffffff80000000`, lower mask `LM=0x7fffffff`, and `mag[0]=0`, `mag[1]=0xB5026F5AA96619E9`: for `i=0..155`, set `x=(mt[i]&UM)|(mt[i+1]&LM)` and `mt[i]=mt[i+MM]^(x>>1)^mag[x&1]`; for `i=156..310`, use the same expression with `mt[i+(MM-NN)]`; finally combine `mt[311]` with `mt[0]` and set `mt[311]=mt[MM-1]^(x>>1)^mag[x&1]`. Consume from index zero. Temper each result with, in order, `x ^= (x>>29)&0x5555555555555555`, `x ^= (x<<17)&0x71D67FFFEDA60000`, `x ^= (x<<37)&0xFFF7EEE000000000`, and `x ^= x>>43`. All arithmetic is unsigned modulo 2^64. A uniform draw is `(x>>11)/9007199254740992.0`.

`executable sample [-2] [-s seed] input amount` samples complete records and preserves their format, content, and comments. Default seed is 11. Parse `amount` as floating point. If it is at least 1, treat it as a count `floor(amount+0.499)`; notably `1.0` means one record. Otherwise it is a sampling fraction.

Fraction mode draws once per record and emits that record in input order iff the draw is below the fraction. Count mode uses reservoir slots: for the 1-based record number `n`, draw `r`, choose slot `n-1` when `n-1<count`, otherwise `floor(r*n)`, and replace the slot if it is below `count`. At EOF emit populated slots in slot-number order. A zero count emits nothing; a count exceeding input size emits every nonempty record in input order.

`-2` count mode makes the same reservoir choices on a first pass, then emits the chosen 1-based record indices in original input order on a second pass. It therefore may order records differently from ordinary reservoir output. It cannot use `-` as input: print `[E::stk_sample] in the 2-pass mode, the input cannot be STDIN.` and exit 1. For fraction input, ignore `-2` (with a warning) and use streaming fraction mode. Applying the same seed to equal-length paired files must select corresponding indices.

## Spec 8

`executable subseq [-t] [-s] [-l width] input region-file` extracts records in input-file order and region rows in their order for each matching name. The region file format is:

- name only: full sequence;
- name plus one positive coordinate `p`: the single base `[p-1,p)`;
- name, start, end: zero-based half-open `[start,end)`;
- with `-s`, parse tab-delimited BED6 and use column 6 as strand (`-` means reverse complement; all other values copy forward).

Missing requested names are silent. Clamp an end beyond sequence length. If start is at least sequence length, skip it and write `[subseq] NAME: START >= LENGTH` to standard error. A zero-length interval is emitted as a header with no separate sequence-content line. Overlapping or duplicate intervals are never merged.

Without `-t`, use FASTA/FASTQ record output. Full-name extraction keeps the original header. A coordinate extraction appends `:START1-END`, where `START1=start+1` and `END` is the clamped zero-based exclusive endpoint (also the conventional 1-based inclusive end). Preserve the original comment after that suffix. Preserve and slice quality for ordinary FASTQ extraction. `-l` wraps both sequence and quality; default 0 is one line. Strand mode is required for FASTA and emits its sequence on one line; minus strands use the complement rules in Spec 6.

With `-t`, emit only `name`, `start+1`, and sequence, separated by tabs; omit markers, comments, quality, and coordinate suffixes. For example `[0,8)` is `name\t1\tSEQUENCE`.

If the region file cannot be read, exit 1 and write `[E::stk_subseq] failed to read the list of regions in file 'PATH'`. Missing required arguments print usage and exit 1.

## Spec 9

`executable size [input]` counts parsed records and total sequence characters, then emits exactly `record_count<TAB>base_count<NEWLINE>`. FASTA and FASTQ, gzip, `-`, empty input, and input from standard input with no filename are supported. Empty input produces `0\t0`.

`executable comp [-u] [-r regions] [input]` emits one tab-delimited composition row per sequence, including a zero-length named sequence. With no regions the 13 fields are:

`name, length, #A, #C, #G, #T, #2, #3, #4, #CpG, #tv, #ts, #CpG-ts`.

Use the IUPAC sets A={A}, C={C}, G={G}, T={T}, M={A,C}, R={A,G}, W={A,T}, S={C,G}, Y={C,T}, K={G,T}, V={A,C,G}, H={A,C,T}, D={A,G,T}, B={C,G,T}, N={A,C,G,T}. Count singleton symbols in A/C/G/T and symbols with set sizes 2, 3, or 4 in `#2/#3/#4`. By default case is ignored; with `-u`, lowercase positions contribute to no count, though reported length remains the full length.

Classify R and Y as transitions (`#ts`); classify the other size-2 symbols as transversions (`#tv`). A position is CpG-associated when it is C or Y followed by G or R, or G or R preceded by C or Y. Count both endpoints, so `CGCGCGCGCG` has `#CpG=10`. A CpG-associated R or Y also increments `#CpG-ts`.

With `-r`, a two-field row containing a name and one positive coordinate `p` selects `[p-1,p)`, and a three-field row containing a name, start, and end selects `[start,end)`. Unlike non-strand `subseq`, a matching name-only row is not a valid full-sequence request: processing it terminates the process with `SIGSEGV`. For example, with sequence input `>x` / `ACGT` and region rows `x 2` followed by `x`, the process produces no standard output or diagnostic before `SIGSEGV` (shell status 139). For valid intervals, emit one row per matching interval as `name, start, end` followed by the same 11 count fields (there is no separate length field), and report the requested end verbatim even when it exceeds the sequence length. Do not import `subseq`'s end-clamping behavior. The implementation also scans through that requested end; beyond the valid sequence buffer, allocator/process memory bytes can contribute to the count fields. Consequently those out-of-range contributions can differ between identical invocations, while the unmodified requested end and the in-range contributions remain deterministic. Names absent from the region file emit no rows. Empty input emits nothing.

## Spec 10

`executable fqchk [-q threshold] input` analyzes only FASTQ records having quality; FASTA records are ignored. Interpret qualities as Phred+33 and cap values above 93 at 93. Classify bases case-insensitively into A, C, G, T, and N/other. Default threshold is 20.

The first line is:

`min_len: MIN; max_len: MAX; avg_len: %.2f; D distinct quality values`

Then print `POS<TAB>#bases<TAB>%A<TAB>%C<TAB>%G<TAB>%T<TAB>%N<TAB>avgQ<TAB>errQ<TAB>%low<TAB>%high`. Emit an `ALL` aggregate row and one row numbered from 1 through maximum read length. Base percentages, average quality, error quality, and low/high percentages use one decimal place. Low means `Q < threshold`, strictly; high is the remainder.

For a row containing `sum` bases, `avgQ=sum(Q)/sum`. Define error probability `p(Q)=10^(-Q/10)`, except Q=0,1,2,3 all use 0.5. Then `errQ=-4.343*ln((sum(p(Q))+1e-6)/(sum+1e-6))`. Positional rows include only reads reaching that position.

With `-q 0`, replace `%low/%high` columns by one `%Qn` column, in increasing quality order, for every quality value occurring anywhere; values use two decimal places. With no qualifying reads, reproduce the observable empty report: minimum is `9223372036854775807`, maximum 0, average and composition/average values are `-nan`, distinct count is 0, and aggregate `errQ` is `-0.0`. A missing input argument prints usage and exits 1.

## Spec 11

`executable trimfq [-q error_rate] [-l min_length] [-b left] [-e right] [-L maximum] input` preserves names, comments, input FASTA versus FASTQ format, and sliced qualities. Defaults are error rate 0.05, minimum length 30, left/right 0, and maximum disabled.

If left or right is nonzero, or `-L` is positive, use fixed trimming and disable quality trimming. Set `begin=left`, `end=sequence_length-right`; if `begin>=end`, set both to zero. Then, if `-L` is positive and `end-begin` exceeds it, set `end=begin+L`. Emit the exact slice `[begin,end)`. Thus over-trimming emits a valid header, empty sequence, bare `+`, and empty quality for FASTQ.

Otherwise, sequences whose quality length is at most `min_length` remain unchanged. For a longer quality string, implement Mott trimming. For each quality byte `b`, clamp `b` into [36,127], let `p=10^(-(b-33)/10)`, and add `error_rate-p` to a running score. Track the highest strictly greater score and its segment; whenever the running score becomes negative, reset it to zero and start after that position. If no positive maximum is found, initially choose the first `min_length` bases. If the best segment is shorter than `min_length`, choose the length-`min_length` quality window with greatest sum of `(quality_byte-33)`, taking the earliest on ties. A 100-base read of 60 `I` qualities followed by 40 `!` qualities trims to its first 60 bases under the defaults.

Missing input prints usage and exits 1; `-` reads standard input.

## Spec 12

`executable mergepe input1 input2` reads one record from each input alternately and emits R1 record 1, R2 record 1, R1 record 2, R2 record 2, and so on, preserving FASTA/FASTQ data and comments. Stop at the shorter file. If input 2 ends first, write `[W::stk_mergepe] the 2nd file has fewer records.`; if input 1 ends first while input 2 still has a record, write the corresponding `1st file` warning. Both warnings end in newline. The already paired records remain in standard output. Missing arguments or files exit 1 with usage/open diagnostics.

`executable dropse [input]` scans one interleaved FASTA/Q stream and emits only adjacent pairs. Two adjacent names pair if their full names are identical, or if they have equal lengths, both end in slash plus a digit, and their prefixes before those final two bytes are identical. A nonmatching pending record is discarded and replaced by the current record. An unmatched final record is discarded. Preserve accepted names, sequences, qualities, and FASTA/FASTQ form in normalized record formatting. Preserve comments except for this pending-replacement quirk: a replacement record's nonempty comment replaces the pending comment, but an empty comment does not clear the pending comment. The first record of a later accepted pair can therefore inherit the last nonempty comment held by the pending slot; the second, current record does not. For example, after accepting `x/1 c1` with `x/2 c2`, an accepted commentless pair named `same` is emitted with first header `>same c1` and second header `>same`. `-` or omitted noninteractive input reads standard input.

## Spec 13

Use this IUPAC bit representation for merge operations: A=1, C=2, G=4, T=8, M=3, R=5, S=6, V=7, W=9, Y=10, H=11, K=12, D=13, B=14, N=15; bitmask 0 renders as `X`. Rendering is uppercase when the position remains trusted and lowercase otherwise.

`executable mergefa [-i|-m] [-h] [-r] [-q N] input1 input2` processes records positionally while input1 has records, always uses input1's name, and emits FASTA wrapped at 60 bases with no comments or quality. For name or length mismatches, warn respectively `[stk_mergefa] Different sequence names: A != B` and `[stk_mergefa] Unequal sequence length: A != B`. Merge only through the shorter sequence length.

Before merging, a FASTQ base with Phred+33 quality less than `N` is made lowercase. Unknown symbols map to N. By default a position is uppercase only if both input characters were uppercase, and output is the IUPAC union (`mask1 | mask2`). Modes alter this:

- `-i`: output the intersection. It is lowercase X when the intersection is empty. The position starts trusted if either input character was uppercase.
- `-m`: also output the intersection and starts trusted if either character was uppercase; force lowercase if either mask is N or the intersection is empty. This preserves the informative allele in lowercase when paired with N.
- `-h`: after normal trust calculation, force output lowercase if either input symbol has more than one possible allele.
- `-r`: use the deterministic allele-selection procedure below rather than unconditional union.

Using the pre-mode trust value, accumulate five counts: same homozygous bases, differing homozygous bases, homozygous/heterozygous, heterozygous/homozygous, and heterozygous/heterozygous. After all output, write exactly `[stk_mergefa] (same,diff,hom-het,het-hom,het-het)=(a,b,c,d,e)` plus newline to standard error.

`-i` and `-m` together are invalid: write a message containing `cannot be applied at the same time` and exit 1. Missing inputs print usage and exit 1.

## Spec 14

For `mergefa -r`, initialize a POSIX-compatible 48-bit generator with seed 11: state is `(11 << 16) + 0x330e`; every `lrand48` step is `state=(0x5deece66d*state+0xb) mod 2^48`, returning `state>>17`. Apply these rules per position:

- two homozygous inputs: output their union;
- one homozygous and one size-2 heterozygous input sharing an allele: consume one random value; if its low bit is 1 output the intersection, otherwise the union;
- two identical size-2 heterozygous inputs: consume one random value; on a low bit of 0 retain the heterozygous code; on 1 consume another and choose its higher set allele when that low bit is 1, otherwise its lower set allele;
- all other combinations render the first input's IUPAC mask in lowercase.

This seeded behavior is exact. For the tested W-versus-A first position, it produces A. Options may be combined according to the transformations above.

## Spec 15

`executable famask source mask` processes corresponding records and positions through the shorter sequence. Emit FASTA using the source name, no comment, and 60-base wrapping. Warn on differing names and lengths with the same `Different sequence names` and `Unequal sequence length` form as `mergefa` (using `[stk_famask]`). At each position, mask byte lowercase `x` lowercases the source byte; uppercase `X` preserves the source byte; every other mask byte replaces the source byte verbatim. Empty corresponding sequences still emit their source header.

`executable mutfa input snp-file` reads whitespace-delimited mutation rows of at least four columns: sequence name, 1-based position, ignored old value, and replacement. Accept a row only when replacement is exactly one alphabetic byte. Apply accepted rows to matching records; silently ignore positions beyond sequence length. Rows are applied in file order, so the last row for a duplicate position wins. Emit every input record as FASTA, name only, wrapped at 60 bases. An empty mutation file is a pure sequence pass-through in that normalized format. Missing arguments print usage; a missing SNP or sequence file reports an open error and exits 1.

## Spec 16

`executable listhet input` emits one line for each sequence symbol whose IUPAC set has exactly two members: `name<TAB>1-based-position<TAB>original-character`. The recognized codes are M, R, S, W, Y, and K in either case. A/C/G/T, three-base codes B/D/H/V, N, and unknowns are not reported. Preserve the character's case. Empty input and zero-length records emit nothing.

`executable hety [-w window=50000] [-t starts=5] [-m] input` classifies each base as called homozygous (IUPAC set size 1), called heterozygous (size 2), or masked (size greater than 2). With `-m`, every lowercase byte is masked before classification. Let `step=floor(window/starts)`.

Maintain counts over the most recent `window` bases while visiting positions `i=0..length`, using a circular buffer. Before adding position `i`, emit when `(i>=window and i mod step=0)` or `i==length`. Normally the report uses the current rolling counts. At the final emission when `length>=window`, first remove positions from `length-window` up to (but not including) the prior reported endpoint. This makes the final counts cover only the trailing partial interval since that endpoint; regular step reports still use a full rolling window. Emit only if called homozygous plus called heterozygous is nonzero:

`name<TAB>previous_endpoint<TAB>i<TAB>rate<TAB>called<TAB>heterozygous`

where `rate = heterozygous / called * window`, printed with two decimals. Then set `previous_endpoint=i`. This intentionally means the numeric interval columns do not always describe the bases used for the rolling counts. A sequence shorter than the window is one partial interval but still multiplies its rate by the full configured window.

There is no guard against `step=0`. When `starts > window`, a record whose length reaches `window` evaluates `i mod step` at `i=window` and the process is killed by `SIGFPE`. For example, `hety -w3` on the records `>x`/`NNBDV` and `>z` produces no standard output or diagnostic before `SIGFPE`. Subject to that zero-step crash, zero-length and all-masked emission points emit nothing.

## Spec 17

`executable gap [-l minimum] input` reports maximal runs of bytes that are not case-insensitive A, C, G, or T. Default minimum is 50. For every run whose length is at least the minimum, emit `name<TAB>zero-based-start<TAB>exclusive-end`. Runs at either sequence boundary and lowercase `n` are handled. Empty records and records without qualifying runs emit nothing.

`executable gc [-w] [-f fraction] [-l minimum] [-x dropoff] input` reports high-GC regions, or high-AT regions with `-w`. Defaults are fraction 0.6, minimum length 20, and dropoff 10.0. In GC mode a hit is C, G, or S; in AT mode it is A, T, or W (case-insensitive). Other IUPAC symbols are misses. Set `q=(1-fraction)/fraction` and scan each sequence independently with score and maximum initially zero:

- A hit starts a candidate at its index when score is zero, adds `q`, and updates the best score/end/hit count only on a strict increase.
- A miss subtracts 1 only while score is positive. If score becomes negative or `best-score > dropoff`, emit the best candidate if its length is at least the minimum, reset, and resume scanning just after the best endpoint.
- At sequence end, emit a remaining best candidate meeting the length requirement.

Each row is `name<TAB>start<TAB>exclusive-best-end<TAB>number-of-hit-bases`, with zero-based half-open coordinates. Empty records emit nothing.

## Spec 18

`executable cutN [-n minimum=1000] [-p penalty=10] [-g] input` finds scored N tracts. Here an N position is a case-insensitive N or another byte mapped to the all-four-bases mask; ordinary two- and three-base IUPAC codes are non-N for this command. In this command's input mapping, `X` and `x` are non-N, while unrecognized bytes such as `Z` and `?` are treated as N positions.

Starting at the next N, scan forward while the prior running score is nonnegative, adding 1 for N and subtracting `penalty` for non-N; retain the endpoint of each strict new maximum. From that endpoint scan backward with the same scoring and retain the start of each strict maximum. This may bridge small non-N islands. Accept the resulting `[start,end)` cut when `end-start >= minimum`; otherwise continue searching after its forward endpoint.

Without `-g`, emit all nonempty sequence pieces outside accepted cuts. Headers are `>name:START-END` or `@name:START-END`, where START is 1-based and END is the zero-based exclusive endpoint/1-based inclusive endpoint. Wrap at 60, and slice and emit qualities for FASTQ. `cutN` FASTQ output has a command-specific serializer quirk: after the bare `+` line, emit an additional empty line before the first quality line. Even an uncut record is renamed `name:1-length`. Do not emit empty leading/trailing pieces. With `-g`, emit only accepted gaps as `name<TAB>start<TAB>end` and no sequence; preserve the implementation behavior that a gap whose start is exactly zero is not printed in this mode. `-` is supported; missing input or files produce the standard diagnostics.

## Spec 19

`executable hpc [input]` performs case-sensitive homopolymer compression: replace each maximal run of identical bytes by its first byte. Thus adjacent `A` and `a` are distinct runs and original case is retained. Emit FASTA only, using names without comments and one sequence line, discarding FASTQ qualities. Skip zero-length records entirely. `-`, or omitted input in a noninteractive invocation, reads standard input.

`executable rename [input [prefix]]` renames records sequentially from 1, with no separator: default names are `1`, `2`, ... and a prefix gives `prefix1`, `prefix2`, ... . Preserve FASTA/FASTQ, sequence, and quality. Comments are preserved except for a pending-record replacement quirk: when a nonmatching current record replaces the pending record, its nonempty comment replaces the pending comment, but an empty comment does not clear the pending comment. A later emitted pending record can therefore inherit the last nonempty comment held in that slot; a current record emitted directly as the second member of a pair does not. For example, input `>old c` / `A` / `>other` / `B` is emitted as `>1 c` / `A` / `>2 c` / `B`. Adjacent records considered a pair under the `dropse` name rule receive the same number, after which numbering advances once. Other records advance individually. A no-argument noninteractive invocation reads standard input, so empty input succeeds with empty output.

## Spec 20

`executable split [-n count] [-l width] prefix input` creates exactly `count` output files, including empty ones, named `prefix.00001.fa` through `prefix.COUNT_AS_5_DIGITS.fa`. Defaults are 10 files and unwrapped output. Distribute record 1 to file 1, record 2 to file 2, wrapping round-robin after `count`; preserve normalized FASTA/FASTQ data and comments, and wrap sequence and quality at `width` when positive. `-` is valid input. Failure to create an output file is an error; no arguments print usage and exit 1.

`executable randbase input` emits FASTA (name only, comments/qualities discarded), wrapping at 60. Leave ordinary bases and IUPAC symbols having other than two possible bases unchanged. Resolve every size-2 symbol independently and equiprobably to one of its standard alleles, preserving the input letter case. Use the 48-bit recurrence described in Spec 14, but initialize the state to zero; a `drand48` draw first updates the state and then equals `state/2^48`. Choose the second allele in A,C,G,T bit order when the draw is below 0.5, otherwise the first. Thus input sequence `AMRSWYKmrsywkNBDHVX` emits `ACGGTTTcgcttgNBDHVX`. Missing input prints usage and exits 1; `-` reads standard input.

## Spec 21

`executable hrun input [minimum]` reports case-sensitive maximal runs of identical bytes, with default minimum 7. A run meeting `length >= minimum` is `name<TAB>zero-based-start<TAB>exclusive-end<TAB>byte`. Minimum 0 behaves like 1 for nonempty runs. Names are truncated at first whitespace. FASTA, FASTQ, gzip, and `-` are supported.

Preserve this command's terminal-run quirk exactly: when transitioning to a different byte within a record, emit the completed run normally. Do not emit the final run at the end of each record inside the record loop. After all records have been processed, emit only the terminal state left by the final record if it meets the threshold. Therefore a qualifying run at the end of a nonfinal record is lost. An empty final record suppresses that preceding run but leaves a synthetic length-one run containing the zero byte: with input `>x` / `AAAA` / `>empty` and minimum 1, emit the 12 bytes `empty<TAB>0<TAB>1<TAB>NUL<NEWLINE>`, where `NUL` is one raw `0x00` byte. N is treated as an ordinary case-sensitive byte, subject to the same quirk. No arguments print `Usage: seqtk hrun <in.fa> [minLen=7]` and exit 1.

## Spec 22

`executable kfreq kmer [input]` accepts a case-insensitive A/C/G/T query of length `k` and emits one five-column row per input record:

`name<TAB>sequence_length<TAB>strand<TAB>neighbor_count<TAB>exact_count`.

For each length-k window consisting only of case-insensitive A/C/G/T, form both the forward word and its reverse complement. An N/other byte clears the rolling window. Define the neighbor set as all words obtainable by changing any one query position to any of A/C/G/T, including leaving it unchanged; equivalently, query words at Hamming distance at most one.

For each valid window, increment forward exact count if forward equals the query, otherwise increment reverse exact count if reverse complement equals it. Independently, increment forward neighbor count if forward belongs to the neighbor set, otherwise increment reverse neighbor count if the reverse complement belongs. Choose `+` only when forward neighbor count is strictly greater than reverse neighbor count; choose `-` on a tie. Report the neighbor and exact counters belonging to the chosen strand. Empty or shorter records produce zero counts and therefore `-`. Query lengths through at least 10 must work. The input defaults to standard input when omitted or may be `-`; gzip is supported. No query prints `Usage: seqtk kfreq <kmer> <in.fa>` and exits 1; a missing file exits nonzero with the standard open error.

## Spec 23

`executable telo [-m motif] [-p penalty] [-d max_drop] [-P] [input]` detects telomere-like sequence at both ends. Defaults are motif `CCCTAA`, penalty 1 (use its absolute value), maximum score drop 2000, and a fixed reporting score threshold of 300. The motif must contain only A/C/G/T. Construct a set containing every cyclic rotation of the motif, with motif length `k`.

For the 5-prime scan, move left to right, maintaining the most recent valid k-mer; ambiguity resets its valid length. A hit means the k-mer is a motif rotation. Before updating score at index `i`, `-P` emits `P<TAB>name<TAB>i<TAB>score<TAB>best`. Starting when `i>=k`, add 1 for a hit or subtract `penalty`; track strict new maxima and their index. Stop if `best-score > max_drop`. If best is at least 300, normally emit `name<TAB>0<TAB>best_index+1<TAB>full_length`, add that interval length to the telomere total, and exclude it from the other-end scan.

For the 3-prime scan, move right to left over the remaining sequence while building complemented k-mers and matching the same rotation set. In profile mode, before scoring emit `Q<TAB>name<TAB>distance_from_right_starting_at_1<TAB>score<TAB>best`. Begin scoring when that distance is at least `k`; use the same score/drop rules. A qualifying result normally emits `name<TAB>best_index<TAB>full_length<TAB>full_length` and adds `full_length-best_index` to the telomere total.

With `-P`, emit scoring profile rows instead of BED-like detected-region rows, but still compute totals. After all inputs, always write `total_telomere_bases<TAB>total_input_bases<NEWLINE>` to standard error. Empty input therefore has empty stdout and `0\t0` on stderr. `-m` changes the motif, `-p` the miss penalty, and `-d` the stopping drop. FASTA/FASTQ, `-`, and omitted noninteractive standard input are accepted.
