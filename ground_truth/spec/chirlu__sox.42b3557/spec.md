# Executable behavioral specification

This file is the authoritative behavioral contract for the required artifact.  The
other files in this directory are background documentation and licensing material;
they may clarify terminology, but an implementation is evaluated against the
requirements below.  The required artifact is one executable file named exactly
`executable`.

## Spec 1

`executable` shall implement the command-line audio processor and audio-information
utility behavior of the native SoX 14.4.2 program.  “SoX-compatible” below means
compatibility with that version's sample conversion, rounding, headers, diagnostics,
and DSP—not merely accepting similarly named options.  This compatibility identity is
important because tests compare some output audio, statistics, help text, and error
messages to output produced by SoX 14.4.2.

The executable is invoked directly; no second `sox` or `soxi` artifact is supplied or
required.  Its process exit status, stdout, stderr, files written, and file metadata
are observable.  Successful processing exits zero except for the explicitly documented
plot-mode behavior in Spec 36.  Parse, open, format, and effect errors exit nonzero.  It
must process the short test signals within a few seconds and must not crash or hang on
empty, truncated, corrupt, or unusually short inputs, except for the two reproducible
global-`--norm` crashes documented in Spec 6.

## Spec 2

The normal grammar is:

```text
executable [global-options] [[format-options] input]...
           [format-options] output [effect [effect-options]]...
```

Format options immediately preceding a filename belong to that file.  Global options
may appear anywhere before the first effect.  Effect arguments follow the effect they
configure.  The program reads every input into an internal multichannel signal,
combines the inputs, runs effects from left to right, and encodes the result to the
output.  Unless overridden, output rate, channels, and encoding are inherited where
the output format permits.  An output rate or channel count different from the input
causes the corresponding implicit rate/channel conversion even when no explicit
effect is present.

Effects may be chained.  Each effect receives the signal and metadata produced by its
predecessor; effects that change length, rate, or channels update the metadata seen by
later effects and the output writer.  Floating-point internal samples represent
nominal full scale as -1 through +1.  Integer reads/writes, clipping, quantization,
dither, and warning counts shall use SoX 14.4.2 conventions.

## Spec 3

The special filename `-` means stdin in an input position and stdout in an output
position.  Headered WAV data must stream correctly through either side, including a
WAV-to-WAV pipe chain.  For headerless stdout, options such as `-t raw`, rate,
encoding, bits, and channels determine the bytes.  Binary audio goes only to stdout;
diagnostics and analysis go to stderr.

`-n`/`--null` is the null handler.  As an input it supplies an indefinite silent
signal suitable for `synth`; as an output it discards audio while still running all
effects.  If its input attributes are omitted, the tested default is one channel at
48000 Hz with 32-bit precision.  `-p`/`--sox-pipe` is equivalent to `-t sox -`.
`--no-glob` makes the following filename literal.  Reading a file whose header length
is deliberately wrong must honor the header normally and read to physical EOF when
`--ignore-length` is attached to that input.

## Spec 4

`--version` writes exactly one stdout line of the form:

```text
<argv0>:      SoX v14.4.2
```

where enough spaces follow the colon to produce the standard SoX 14.4.2 layout (for
`/workspace/executable`, six spaces), and exits zero.  `-h` and `--help` are equivalent,
exit zero, begin with the same version line, and print the standard SoX 14.4.2 usage
summary.  The help must include the sections `SPECIAL FILENAMES`, `GLOBAL OPTIONS`,
`FORMAT OPTIONS`, `AUDIO FILE FORMATS`, and `EFFECTS`; list all options, formats, and
effects required by this specification; and show defaults of 8192 bytes for buffers,
verbosity 2, and DFT minimum 10.

The advertised built-in format line is:

```text
AUDIO FILE FORMATS: 8svx aif aifc aiff aiffc al amb au avr cdda cdr cvs cvsd cvu dat dvms f32 f4 f64 f8 fssd gsrt hcom htk ima ircam la lpc lpc10 lu maud nist prc raw s1 s16 s2 s24 s3 s32 s4 s8 sb sf sl sln smp snd sndr sndt sou sox sph sw txw u1 u16 u2 u24 u3 u32 u4 u8 ub ul uw vms voc vox wav wavpcm wve xa
```

The advertised effect line is:

```text
EFFECTS: allpass band bandpass bandreject bass bend biquad chorus channels compand contrast dcshift deemph delay dither divide+ downsample earwax echo echos equalizer fade fir firfit+ flanger gain highpass hilbert input# ladspa loudness lowpass mcompand noiseprof noisered norm oops output# overdrive pad phaser pitch rate remix repeat reverb reverse riaa silence sinc speed splice stat stats stretch swap synth tempo treble tremolo trim upsample vad vol
```

## Spec 5

`--help-effect NAME` prints standard effect usage and exits 1, including for a valid
name.  `NAME=all` prints usage for every advertised effect (including, at minimum,
complete entries for `gain`, `reverb`, and `echo`) and is a substantial listing of
more than 250 lines.  The exact `gain` synopsis and option meanings are:

```text
gain [-e|-b|-B|-r] [-n] [-l|-h] [gain-dB]
-e	 Equalise channels: peak to that with max peak;
-B	 Balance channels: rms to that with max rms; no clip protection
-b	 Balance channels: rms to that with max rms; clip protection
	   Note -Bn = -bn
-r	 Reclaim headroom (as much as possible without clipping); see -h
-n	 Norm file to 0dBfs(output precision); gain-dB, if present, usually <0
-l	 Use simple limiter
-h	 Apply attenuation for headroom for subsequent effects; gain-dB, if
	   present, is subject to reclaim by a subsequent gain -r
gain-dB	 Apply gain in dB
```

`--help-format NAME` likewise prints the format description and exits 1.  `all` must
include detailed entries for at least WAV, AU, and AIFF and exceed 2000 bytes.  WAV
help identifies it as Microsoft's format, readable and writable, with signed PCM at
16/24/32 bits, unsigned PCM at 8 bits, 8-bit `u-law` and A-law, 4-bit MS and IMA ADPCM,
and floating PCM at 32/64 bits.  Unknown effect/format names fail and print the full
valid effect/format list.  XA help describes Maxis XA ADPCM and reports `Reads: yes`
and no write encodings.

## Spec 6

Diagnostics use the standard prefixes `<argv0> INFO component:`, `WARN`, and `FAIL`,
and go to stderr; normal help and information output go to stdout.  Default verbosity
is 2.  `-V3` reports input and output properties and every effect-chain stage, and
repeated `-V` flags increase verbosity.  `-VLEVEL` selects a numeric level.  Quiet
mode `-q`/`--no-show-progress` suppresses informational and warning chatter but not
fatal failures.  Errors must contain a useful reason and affected filename or
parameter.  Standard SoX wording and whitespace are required where diagnostics are
compared byte-for-byte.

Clipped samples are saturated and a warning reports clipping and, where standard SoX
does so, its sample count.  `-G`/`--guard` adds headroom/temporary processing, but it
does not prevent an explicitly requested effect from clipping internally.  In
particular, with mono 8000-Hz signed-16 raw input samples `20000, -20000, 10000`, the
options `-R -D -G`, signed-16 raw output, and `gain 20` exit zero, write the saturated
samples `32767, -32767, 32767`, and write this stderr line:

```text
/workspace/executable WARN gain: gain clipped 3 samples; decrease volume?
```

Global `--norm` normally combines guarding and normalization.  Two reference bugs are
part of the observable contract: `--norm -n OUTPUT synth 0.1 sine 440 vol 3`
terminates by signal 11 with empty stdout and stderr, as does `-R -D --norm` on a
two-sample signed-16 raw input when writing signed-16 raw through `gain 20`.
`--temp DIRECTORY`, `--dft-min NUM`, `--single-threaded`, `--multi-threaded`, and
`--replay-gain off` are accepted and preserve the processing result expected from the
reference implementation.

## Spec 7

The global buffering options are `--buffer BYTES` and `--input-buffer BYTES`; valid
tested sizes include 1024, 4096, and 16384 and must not alter audio results.  A missing
argument, nonnumeric value, or a size below 16 is an error.  `-D`/`--no-dither`
disables automatic dither.  `-R` uses the standard repeatable random seed.  `SOX_OPTS`
is tokenized as extra command-line options and, in particular, can supply `-D`.

`--effects-file FILE` reads effect chains from a text file; a missing file fails.  Each
nonempty line is a separate chain applied to the next portion of the input stream, not
another effect appended to the preceding line.  Effect names and arguments on one line
form one sequential chain.  Thus `trim 0.01 0.02` followed by `gain -6` on the next
line produces 720 frames from a 0.1-second 8000-Hz input, whereas putting both effects
on one line produces 160 frames.

`--plot gnuplot` and `--plot octave` cause a filter invocation to emit the appropriate
response-plot script.  `--clobber` permits overwriting an existing output; the
noninteractive behavior of `--no-clobber` must refuse or prompt rather than silently
overwrite.  Input `-v FACTOR` applies an independent linear volume multiplier before
combining, and a nonnumeric factor is an error.

## Spec 8

Per-file signal/encoding options are `-r`/`--rate`, `-c`/`--channels`,
`-b`/`--bits`, `-e`/`--encoding`, `-t`/`--type`, `-C`/`--compression`,
`--endian little|big|swap` (short forms `-L`, `-B`, `-x`), `-N` reverse nibbles,
and `-X` reverse bits.  Rates accept integer or decimal Hz and a trailing `k` scale.
Channels is a positive integer.  Supported bit depths depend on the encoding and
container.  Tested encoding names include `signed-integer`, `unsigned-integer`,
`floating-point`, `mu-law`, `a-law`, `ima-adpcm`, and `ms-adpcm`; unambiguous enum
prefixes and mixed case are accepted where standard SoX accepts them, but an empty,
whitespace-only, invalid, or ambiguous value fails with the allowed values.

Nonnumeric/nonpositive rates, channel count zero, a selected unknown type,
incompatible format/encoding combinations, and missing option arguments fail.  For
signed-integer raw output, however, `-b 7` exits zero and warns exactly
`raw can't encode Signed Integer PCM to 7-bit` rather than rejecting the request.
Repeated per-file selectors are resolved before the filename and the last value
controls: for example,
`-t bogus -t raw OUTPUT` succeeds because the unselected `bogus` value is not
validated.

File types are inferred case-insensitively from the final suffix, including paths and
names containing multiple dots.  A name with no suffix is recognized from a
self-describing WAV, AIFF, or AU header.  Headerless data with no inferable type must
be given `-t` and its necessary signal parameters.

## Spec 9

Output comments are controlled by `--comment TEXT` (replace), `--add-comment TEXT`
(append), and `--comment-file FILE` (read text from the named file).  Formats that
support comments, including AIFF, expose them through full information and
annotation-only queries.  WAV/wavpcm is an exception: these options are accepted when
writing it but the text is not serialized; full information contains no comment and
`--info -a` writes no output.  In the absence of an explicit comment, normal SoX
output metadata may use `Processed by SoX`.  Endianness conversion must produce
different and correctly ordered raw bytes; `swap`, reverse-bit, and reverse-nibble
transformations are reversible and match SoX's byte transforms.

Output precision/encoding requests must be reflected both in bytes and subsequent
metadata.  Raw sizes are exact: one second of 8000-Hz mono u8/mu-law/A-law is 8000
bytes; s16 is 16000 bytes; f32 is 32000 bytes.  A 0.01-second 44100-Hz mono u8 synth
contains exactly 441 bytes.

## Spec 10

`--info` and `--i` switch the same executable to SoXI behavior:

```text
executable --info [-V[level]] [-T]
  [-t|-r|-c|-s|-d|-D|-b|-B|-p|-e|-a] file...
```

With no field selector, print standard aligned full information containing input
filename, channel count, sample rate, precision, duration, sample count, file size,
bit rate, sample encoding, and comments when present.  A header-only XA file whose
decoded-size field is zero is an exception: full information exits zero and prints
only `Input File`, `Channels`, `Sample Rate`, `Precision`, and `Sample Encoding`; it
omits duration, sample count, file size, and bit rate for all three accepted magic
variants, stereo rates, and lenient tag values.  `-t`, `-r`, `-c`, `-s`, `-d`,
`-D`, `-b`, `-B`, `-p`, `-e`, and `-a` select respectively type, sample rate,
channels, samples per channel, `HH:MM:SS.xx` duration, decimal seconds, encoded bits,
average bitrate, estimated precision, encoding name, and annotations.  Numeric-only
queries contain no labels.  Rates print as integers when integral; duration seconds
uses fixed decimal formatting compatible with SoXI.

For multiple files, a selected field prints one value per input.  `-T` totals samples
or durations for `-s`, `-d`, and `-D`, including the single-file case.  Other fields
remain per-file.  Missing files, empty unrecognized files, and corrupt headers fail
without crashing.  Verbose information mode includes the standard diagnostic detail.

## Spec 11

WAV reading and writing supports mono, stereo, quad, and six-channel files; 8, 16,
24, and 32-bit integer PCM; 32 and 64-bit IEEE floating PCM; mu-law; A-law; IMA ADPCM;
and MS ADPCM in the combinations allowed by WAV.  It preserves rate, channels,
duration/sample count, and encoding through conversion, but not comments as detailed
in Spec 9.  Tested rates span 8000 through 96000 Hz and inputs include odd and
extremely short sample counts.

`wavpcm` is an alias that writes ordinary WAV PCM.  Multichannel or non-PCM WAV may
use the extensible form as standard SoX does.  WAV data must be readable when renamed
without an extension.  Conversions among WAV, AIFF, and AU preserve samples exactly
when both endpoints use the same lossless PCM representation.  Lossy ADPCM round trips
need not restore samples bit-for-bit, but must decode to valid audio with reference
metadata and signal statistics.

## Spec 12

AIFF supports mono and stereo integer PCM at 16, 24, and 32 bits, comments, automatic
header recognition without an extension, and lossless round trips.  AIFC supports at
least the floating/sowt forms exercised by conversion, including 32-bit floating
input metadata.  `aif`, `aiff`, `aifc`, and `aiffc` suffix/type aliases are recognized.

AU/SND supports mono and stereo signed PCM at 8/16/24/32 bits where representable,
32-bit floating PCM, mu-law, and A-law.  It preserves metadata and recognizes its
header without an extension.  Conversions WAV↔AIFF↔AU and chains through all three
must yield valid files with reference sample values, counts, and statistics.

## Spec 13

Raw formats include `raw`, `s8/s16/s24/s32`, `u8/u16/u24/u32`, `f32/f64`, `ul`,
`al`, and their advertised aliases.  `raw` requires explicit signal and encoding
information when it cannot inherit it.  Integer signedness, sample width, interleaved
multichannel ordering, little/big/swap endian selection, bit reversal, and nibble
reversal must match SoX exactly.  Raw-to-WAV-to-raw conversion is lossless when no
precision reduction or lossy codec intervenes.

DAT is the SoX textual sample format.  A written DAT file begins with comment header
lines that identify at least `; Sample Rate <rate>` and `; Channels <count>`, followed
by time/sample rows readable back by this executable.  DAT round trips preserve rate,
channel count, and sample values at its text precision.

## Spec 14

The executable must read and write the following legacy/container formats in the
standard SoX layouts and preserve their representable metadata on round trip:
`8svx`, `avr`, `cdda`/`cdr`, `hcom`, `maud`, `nist`/`sph`, `sf`/`ircam`, `sln`,
`smp`, `sndt`, `sndr`, `txw`, `voc`, `vox`, `vms`/`dvms`, `wve`, and native `sox`.
VOC covers mono and stereo, unsigned 8-bit and signed 16-bit data, multiple sample
rates, auto-detection, corrupt/truncated-header rejection, and conversion to/from VOX.

Observe format constraints and defaults: CDDA is stereo 44100-Hz signed 16-bit and its
writer rounds storage up to complete 2352-byte sectors, each representing 588 stereo
sample frames.  Thus a 441-frame stereo input writes one 2352-byte sector and reads
back as 588 frames; the sector padding is part of the decoded length.  HCOM is mono
and commonly 11025/22050 Hz; SLN is headerless signed 16-bit mono with a
tested 8000-Hz interpretation; WVE and PRC are mono 8000-Hz telephony formats; VOX is
raw mono Dialogic ADPCM and warns/defaults when rate is absent.  When a writer can
coerce an input to a mandated rate/channel/encoding, it shall do so with the same
warning and implicit conversion as SoX rather than producing invalid output.

In particular, 8SVX accepts 44100-Hz stereo output.  A requested 8-bit unsigned
encoding succeeds with 441 frames for 0.01 seconds, warns
`8svx can't encode Unsigned Integer PCM`, and is reported on readback as 8-bit
`Signed Integer PCM` with two channels at 44100 Hz.

## Spec 15

LPC10 is recognized through `.lpc10` and `.lpc`, reports mono, 8000 Hz, 16-bit
precision, and encoding `LPC10`, and supports encode/decode and effect chains.  The
encoder enforces mono/8000-Hz operation by warning and coercing incompatible source
properties as SoX does.  Frame boundaries, truncated-but-readable inputs, longer
signals, and conversions from 24-bit source PCM must not crash and must give the
reference decoded sample counts/statistics.

CVSD is recognized through `.cvsd` and `.cvs`; CVU is the unfiltered CVSD variant.
All three suffix/type cases report exactly `CVSD` for `--info -e`, are mono, support
8-kHz and tested 16-kHz operation/options, and round-trip through WAV.  An unspecified
raw CVU rate emits the standard default rate notice.  LPC10↔CVSD conversions decode
and re-encode correctly, and decoded
signals must have the non-silent amplitude and rough-frequency characteristics of the
reference codecs.

## Spec 16

GSRT reads and writes the Grandstream ringtone layout with mono 8000-Hz mu-law or
A-law data.  It validates checksum and embedded filename fields, rejects invalid
headers, warns and truncates inputs beyond the format's maximum audio size, preserves
metadata on a write/read cycle, and uses the standard even/word-aligned layout.

HTK reads/writes mono sampled waveform data.  Its writer rounds the sample period to
the nearest integer number of 100-ns units, so a rate not exactly representable by
that period is not preserved exactly.  Writing mono signed-16 PCM requested at 11025
Hz exits zero, stores 100 input samples, reports the resulting rate as `11025.4`, and
warns exactly:

```text
/workspace/executable WARN htk: rounding sample period 907.029478 (x 100ns) to nearest integer
```

Reading that HTK file to raw output explicitly requested at 11025 Hz performs the
corresponding implicit rate conversion: it still writes 100 samples, but their bytes
are not identical to the source PCM.  HTK rejects unsupported `parmKind` values with
an `unsupported HTK type` diagnostic.

PRC reads Psion Record A-law and IMA ADPCM forms, reports mono 8000-Hz metadata and
the appropriate 8-bit A-law or 4-bit IMA ADPCM encoding, rejects non-PRC headers, and
supports reference-compatible write/read conversion.

## Spec 17

XA is a read-only Maxis EA-ADPCM handler.  `.xa` selects it and `-t xa` selects it
explicitly.  A 24-byte little-endian header contains: one of `XA\0\0`, `XAI\0`, or
`XAJ\0`; uint32 decoded size; uint16 tag; uint16 channels; uint32 sample rate; uint32
average byte rate; uint16 alignment; and uint16 encoded bits.  The tag is accepted
leniently, but zero channels and all sample widths other than 16 bits are errors.  A
channel count through uint16 maximum and rates including zero, 8000, 11025, 22050,
and 44100 are parsed without overflow.

Empty, magic-only, truncated, and wrong-magic XA files fail cleanly.  A wrong align
field is replaced with `(bits/8)*channels` and at verbose level reports, for example,
`Invalid sample alignment value 4.  Assuming 2.`  A wrong average byte rate is
replaced with `rate*align` and similarly reported.  A header bits field inconsistent
with valid XA data is corrected only in the same cases as SoX.  Attempting to write
XA fails and must not leave a purported valid XA file.

For a header-only XA whose decoded-size field is zero, the full-information field
omission described in Spec 10 applies to `XA\0\0`, `XAI\0`, and `XAJ\0` headers.

## Spec 18

Multiple input files default to concatenation.  `--combine concatenate` explicitly
selects it; all inputs must have compatible sample rates and channel counts, although
container types may differ.  Samples appear in input order, lengths sum, metadata is
derived as in SoX, effects apply after combination, and requested output resampling
occurs after combination.  `--combine sequence` also processes files serially but
breaks/restarts the output sequence as required on incompatible formats.

`-m`/`--combine mix` sums corresponding samples and scales according to SoX mix
rules; its duration is the longest input with shorter inputs treated as exhausted.
Per-input `-v` is applied first.  Channel mismatches use SoX's warning/mapping behavior
where mix supports them, and clipping is reported.  `--combine mix-power` uses
equal-power normalization.  `-M`/`--combine merge` interleaves input channels in
input/channel order and uses the longest duration.  `-T`/`--combine multiply`
multiplies corresponding samples and uses the reference duration rule.  Incompatible
rates fail rather than being silently combined.

## Spec 19

Time and position parameters accept decimal seconds; `HH:MM:SS` forms; sample counts
with an `s` suffix; and, where the effect grammar permits, positions relative to the
end (`-`) or previous position (`+`) and absolute positions prefixed with `=`.
Durations become integral frames using SoX 14.4.2 rounding.  Multichannel duration is
frames per channel, not total scalar samples.  Unchanged effects preserve rate and
channel count.  Short, one-sample, very-short, large-count, and multichannel inputs
must be handled without buffer-boundary errors.

Effects chains may be loaded from a file using the line-delimited grammar in Spec 7 or
written on the command line.  Analysis effects may terminate a chain at the null
output.  Effects that need to buffer all audio (`reverse`, normalization, some
splice/fade processing) must still compose with earlier and later effects.

## Spec 20

`synth [length] TYPE [COMBINE] FREQ...` measures its length at the effect chain's
current input rate and channel count, before any implicit output-rate conversion.  A
sample-count length with an `s` suffix therefore does not promise that many output
frames when null input at its 48000-Hz default is resampled: `441s` produces 405 frames
at 44100 Hz, `100s` produces 17 frames at 8000 Hz, and `80s` produces 13 frames at
8000 Hz.  A duration in seconds retains that duration through resampling.  Supported
waveform names include `sine`/`sin`, `square`, `triangle`, `sawtooth`, `trapezium`,
deprecated `trapetz`, `exp`, `pluck`, `whitenoise`/`noise`, `tpdfnoise`, `pinknoise`,
and `brownnoise`.
Waveform-specific offset, phase, and p1/p2/p3 parameters implement duty cycle, peak
position, trapezium edges, exponential shape, and pluck decay exactly as SoX.

Frequency accepts Hz, `k`, and percentage/note notation.  `f1:f2`, `f1/f2`,
`f1+f2`, and `f1-f2` select the standard linear, exponential, cycle, and alternate
sweeps; upward and downward sweeps are supported.  Multiple waveform clauses are
combined with `create`, `mix`, `amod`, or `fmod`, distributed/reused across channels
as SoX does.  `-n` disables automatic headroom.  Synth may replace or combine with an
existing input.  Omitting `TYPE` selects the same sine waveform as an explicit `sine`;
for example, an 8000-Hz `synth 1.0` writes 8000 frames, and a deterministic 0.01-second
raw rendering is byte-identical with and without the explicit word `sine`.
A nonnumeric frequency, a sweep with no finite duration, a noise sweep, or an invalid
exponential sweep through zero fails.

## Spec 21

`stat [-s scale] [-rms] [-freq] [-v] [-d]` analyzes audio and writes its report to
stderr without creating audio at a null output.  Default output includes `Samples
read`, `Length (seconds)`, `Scaled by`, maximum and minimum amplitude, midpoint,
mean norm, mean amplitude, RMS amplitude, maximum delta, minimum delta, mean delta,
RMS delta, rough frequency, and volume adjustment.  The alignment-sensitive heading
for mean norm is `Mean    norm` with four ASCII spaces, not `Mean norm`.  `-rms`,
frequency-bin output, hex/sample dump, differential mode, and custom scale use
reference headings,
precision, significant figures, and percentages.

`stats [-b bits|-x bits|-s scale] [-w window-time]` prints per-channel columns for
multichannel input and fields including DC offset, min/max level, peak/RMS dB,
crest factor, flat factor, peak count, bit depth, number of samples, and length.  It
supports 16-bit scaling, hexadecimal scaling, arbitrary scale, and windowing; invalid
bit depth or nonpositive/invalid window time fails.  Numeric formatting—including
`-inf`, significant digits, aligned columns, SI suffixes, and percentage signs—must
match SoX 14.4.2 where golden text is used.

## Spec 22

`gain [-e|-b|-B|-r] [-n] [-l|-h] [dB]` implements linear dB gain, peak
normalization, channel peak equalization, RMS balancing with/without clip protection,
limiting, headroom reservation, and later headroom reclamation.  Options have the
meanings stated in Spec 5 and may be combined only in the combinations accepted by
SoX.  Conflicts such as equalize plus balance, normalize plus restore, or invalid
limiter/headroom combinations fail.  Very large positive/negative gains remain
well-defined and saturate/report clipping as appropriate.  `norm [dB-level]` is the
normalization shorthand.

`vol gain [amplitude|power|dB [limitergain]]` converts its gain by the selected type,
supports negative amplitude gain (phase inversion), optionally soft-limits, and
reports clipping without a limiter.  Invalid type or limiter gain fails.  `contrast
[0..100]`, `loudness [gain [reference]]`, input `-v`, and gain/norm all operate per
sample with standard reference formulas and preserve duration.

## Spec 23

`compand attack,decay... transfer-function [gain [initial-volume [delay]]]` implements
the standard soft-knee dB transfer curve, one attack/decay pair reused for all channels
or one pair per channel, output gain, initial envelope level, and look-ahead delay.
Transfer points and optional knee syntax are parsed exactly as SoX.  Odd attack/decay
lists, negative attack/decay or delay, and invalid initial volume fail.  Stereo
channels retain independent envelopes.

`mcompand` applies multiple quoted compand bands separated by crossover frequencies,
supports two- and three-band compression and stereo input, and uses the standard
crossover filters and recombination.  Insufficient band parameters and invalid
attack/decay fail.  A final unsupported delay parameter is rejected.  Valid high
level output can clip and must produce the standard warning.

## Spec 24

The IIR filter effects `lowpass`, `highpass`, `allpass`, `band`, `bandpass`,
`bandreject`, `bass`, `treble`, `equalizer`, `biquad`, `deemph`, and `riaa` implement
SoX 14.4.2 transfer functions.  Low/high pass support first and second order (`-1`,
`-2`) and optional width.  Band-pass/reject support constant-skirt `-c`.  Bass and
treble implement shelving gain with optional frequency and slope/width.  Equalizer
is a peaking EQ and multiple instances cascade.  Biquad consumes six coefficients.

Frequency accepts Hz or `k`.  Width types are Hz (`h`), kHz (`k`), octaves (`o`), Q
(`q`), and shelf slope (`s`) where applicable.  Defaults and explicit default widths
are equivalent.  Filters apply independently to every channel and preserve length.
Invalid negative widths, missing frequency/width/gain, and other effect-specific
out-of-domain parameters fail.  A cutoff exactly at Nyquist is not rejected:
`lowpass 4000` on an 8000-Hz finite signal exits zero.  Passband preservation,
stopband attenuation, shelf boost/cut, cascades, and stereo behavior must match the
reference within its numeric output tolerances.

## Spec 25

`sinc [-a attenuation|-b beta] [-p phase|-M|-I|-L] [-t transition|-n taps]
[highpass-frequency][-lowpass-frequency ...]` provides low-pass, high-pass, band-pass,
and band-reject FIR designs.  It supports attenuation, Kaiser beta, phase 0–100 and
minimum/intermediate/linear shortcuts, transition bandwidth, odd tap count, rounding,
and independent transition settings on both band edges.  Valid tested edge values
include combined attenuation 100, minimum 101 taps, phase variants, and narrow bands.
Conflicting attenuation/beta or bandwidth/taps settings, missing frequency,
attenuation/phase out of range, and too few taps fail.  The implementation does not
reject every frequency above Nyquist: `sinc 4001` on an 8000-Hz finite signal exits
zero.

`fir [coefficient-file|coefficients...]` convolves each channel with inline or file
coefficients.  A single argument is always the coefficient filename, so `fir 1`
fails with `couldn't open file 1`; an inline unity response can instead be expressed
by the two coefficients `1 0`.  Files and stdin (`-`) allow whitespace and comments.
Unity, short low-pass, and 101-tap filters work; missing/bad files fail.  `firfit` reads
monotonic frequency/gain knots (comments allowed), fits the standard response, and
rejects non-monotonic knots.  `hilbert [-n odd-taps]` generates the standard Hilbert FIR;
even or too-small tap counts fail.  All designs reproduce reference impulse/frequency
responses and delay/length conventions.

## Spec 26

`rate [quality] [override-options] RATE` changes sample rate with standard SoX output
sample counts and band-limited interpolation.  Quality selections are `-q`, `-l`,
`-m`, `-h` (default high), `-v`, and numeric recipes used by SoX.  It supports
integer and noninteger ratios, 8k→48k, 11025→48k, 22050→44100, 44100↔48000,
44100→22050, 96k→44100, and 192k→48k, stereo signals, same-rate passthrough, and
very short audio.  An output `-r` request triggers the equivalent implicit effect.

High-quality overrides include `-M`/`-I`/`-L` or phase, steep filter, aliasing,
bandwidth (valid 74–99.7 percent), rejection, bit depth, anti-alias level, 0-dB
bandwidth, rolloff, disable small-integer optimization, and high-precision clock in
their standard SoX syntax.  Mutually invalid quality/override combinations and
out-of-range bandwidth, phase, rejection, bit depth, or anti-alias values fail.

`downsample [factor=2]` keeps every factor-th frame; valid factor range is 1–16384.
`upsample [factor=2]` inserts factor-1 zero frames between samples; valid range is
1–256.  Both update sample rate and frame count accordingly, work per channel, handle
empty/one-frame/short inputs, and chain with filters, gain, and channels.  Zero,
nonnumeric, or above-limit factors fail.

## Spec 27

`channels N` uses SoX's default channel conversion: duplicate mono to stereo, average
stereo to mono, and perform the standard mapping for other counts.  `remix` supports
one or more output specifications, individual channels, inclusive ranges, channel 0
as silence/ignored input, multiple source channels mixed into one output, and linear
(`vFACTOR`) or dB (`v...dB`) multipliers.  It can select left/right, duplicate mono,
mix stereo to mono, and create several independently specified outputs.

`swap` exchanges adjacent channel pairs, is a null operation on mono, and preserves
the final channel of an odd-channel signal.  For each stereo frame `(L, R)`, `oops`
writes `(L-R, L-R)` without half scaling; for example, `(1000, 200)` becomes
`(800, 800)` and `(-1000, 500)` becomes `(-1500, -1500)`.  `divide` applies the
experimental alternating-channel division behavior: mono is a passthrough and
stereo/multichannel results match SoX's channel pairing and saturation rules.

## Spec 28

`trim start [length|=end]` selects the exact frame range, with seconds, sample counts,
relative/absolute positions, and multichannel frame alignment.  `pad length[@position]
...` inserts zero-valued frames at the beginning, end, or multiple positions while
preserving channels.  `repeat [count]` appends the input that many additional times;
count 0 leaves one copy, count 1 yields two, and large counts have exact summed length.
`reverse` reverses frame order while retaining channel tuples and metadata.

These editing effects compose: trim can limit a repeated stream, reverse can be
followed by gain, and concatenated output can later be split by trim without changing
the selected samples.  Invalid positions or missing required arguments fail rather
than silently creating malformed output.

## Spec 29

`fade [t|q|h|l|p] fade-in [stop-position [fade-out]]` implements linear, quarter-sine,
half-sine, logarithmic, and inverted-parabola curves with exact endpoint and sample
rounding behavior.  It supports fade-in only, fade-out only through a stop position,
both ends, sample-count duration, very short and whole-file fades, and all channels.
Unknown curve types and missing duration fail.

`silence [-l] above-periods duration threshold [below-periods duration threshold]`
detects periods using percent or dB thresholds and follows SoX's period and end-of-file
state behavior; supplying both clauses is not an unconditional trim of both ends.  At
8000 Hz, applying `silence 1 20s 1% 1 20s 1%` to mono signed-16 samples consisting of
100 zeros, 200 copies of `10000`, and 100 zeros exits zero and returns exactly 300
samples: the 200 copies of `10000` followed by all 100 trailing zeros.  It removes the
100 leading zeros but retains the trailing silent span.  The effect optionally leaves
qualifying silence with `-l` and preserves channel structure.  Duration accepts
seconds or samples.  Strict and high-dB thresholds follow SoX comparison conventions.

`splice [-h|-t|-q] position[,excess[,leeway]]...` joins around one or more points
using half-sine, triangular, or quarter-sine crossfades.  It supports default and
zero leeway, custom excess, tiny crossfades, stereo, and chaining two copies of a
signal with reference length/sample transitions.

## Spec 30

`delay position...` delays each channel independently (one delay may be reused),
accepting seconds and sample counts, including zero and long delays; too many channel
arguments fail.  A leading `-` is an end-relative position for finite input, not an
invalid negative duration: delaying a 0.1-second 44100-Hz input by `-0.05` yields
6615 frames, and delaying a two-second 8000-Hz input by `-1` yields 24000 frames.
It fails for an indefinite null input because the end position is then unknown.
`echo gain-in gain-out delay decay...` supports
one or several delay/decay pairs and sample-rate-independent time behavior, including
short delays and zero decay.  Invalid gain/delay/decay or more than the supported
number of echoes fails.  `echos` implements the serial-echo variant.

`reverb [-w|--wet-only] [reverberance [HF-damping [room-scale [stereo-depth
[pre-delay [wet-gain]]]]]]` implements the standard freeverb-style response, default
parameters, wet-only mode, mono/stereo processing, pre-delay, extreme valid room
scale, and effect chaining.  Parameters outside their permitted ranges fail.

## Spec 31

`chorus gain-in gain-out delay decay speed depth -s|-t ...` supports one or multiple
sine/triangle voices, two and three voice setups, stereo-preserving processing, and
the inclusive tested boundaries: gain-in 0 through 1, nonnegative gain-out, delay 20
through 100 ms, decay 0 through 1, speed 0.1 through 5 Hz, and depth 0 through 10 ms.
For example, `chorus 0 0 20 0 0.1 0 -s` and
`chorus 0.7 0.9 20 0.4 0.5 10 -s` both exit zero.  `flanger [delay depth regen width
speed shape phase interp]` supports defaults, sine/triangle shape, linear/quadratic
interpolation, stereo phase, zero delay, and positive/negative regeneration within allowed bounds.
`phaser gain-in gain-out delay decay speed [-s|-t]` supports default/custom sine and
triangle modulation.  `tremolo speed [depth]` applies sinusoidal amplitude modulation
for slow/fast rates and 0–100% depth.

Missing required chorus/tremolo parameters and invalid negative speed/depth fail.
Valid settings preserve the input rate and channels.  High feedback/decay may clip
and must warn.  Chaining modulation effects applies them in order and matches the
reference statistics.

## Spec 32

`tempo [-q] [-m|-s|-l] factor [segment [search [overlap]]]` changes duration without
changing pitch.  It supports quick search, music/speech/linear profiles, explicit
window parameters, stereo and short input, factors from the accepted boundaries 0.1
through 100, and the standard output-length tolerance.  Factors below/above that
range or zero fail.

`speed factor[c]` changes playback rate and pitch together; a `c` suffix expresses
cents.  It accepts tested factors 0.1 through 10 and rejects zero/negative values.
`pitch [-q] cents [segment [search [overlap]]]` shifts pitch while restoring duration,
including ±25, ±50, ±100, ±200, and ±1200 cents and stereo input.

`stretch factor [window fade shift fading]` changes duration with the standard WSOLA
parameters and supports 0.5, 0.8, 1, 1.5, and 2.  `bend [-f frame-rate] [-o oversample]
start,cents,end ...` applies one or several time-local pitch bends, including negative
cents, start zero, end-of-file extension, and a zero-duration point.  All retain valid
metadata and reference duration/sample behavior.

## Spec 33

`overdrive [gain=20 [colour=20]]` implements SoX's nonlinear waveshaping over the full
tested 0–100 parameter range, per channel; nonnumeric/out-of-range input fails.
`dcshift shift [limitergain]` adds a DC offset, optionally applying the standard
limiter, preserves stereo, and reports shifted/clipped samples.  Shift zero is a null
transform.  Values are not restricted to -1 through +1: `dcshift 2` on finite input
exits zero and warns that samples clipped.  Missing/nonnumeric shift fails; valid
small or large limiter gain follows SoX saturation behavior.

`earwax` is the standard headphone spatialization FIR.  It accepts only stereo
44100-Hz input, rejects mono and other rates with the standard diagnostic, and handles
very short signals.  `divide` is as specified in Spec 27.  `contrast`, `oops`, and
other nonlinear/channel effects preserve rate and expose clipping consistently.

## Spec 34

`noiseprof [profile-file]` analyzes mono or multichannel noise and writes a textual
profile either to the named file or, when omitted, to stdout.  The format has one line
per channel beginning `Channel N: ` followed by decimal spectral values separated
strictly by comma plus space (`value, value`), not semicolons.  It is stable across
repeated profiling of the same input and handles very short and long samples and all
tested sample rates.

`noisered [profile-file [amount]]` reads that profile, or reads it from stdin when the
filename is omitted/`-`, and performs FFT-window noise reduction independently per
channel.  Default amount and values 0 through 1 are supported; different values have
monotonic/reference attenuation behavior and windowing may shorten output only as in
SoX.  Missing files, malformed profiles, channel-count mismatch, and amounts outside
0..1 fail.  Stereo/high-noise workflows preserve channels and produce finite,
nonempty audio.

## Spec 35

`vad` detects voice and removes leading non-voice using SoX defaults.  Its filter
options are `-h high-pass-filter` (default 50 Hz) and `-l low-pass-filter` (default
6000 Hz); each accepts a positive frequency (`-h 100` and `-l 3000` exit zero), while
zero and negative values fail.  The allowed-gap control is `-g allowed-gap`, in
seconds, defaults to 0.25, and accepts the inclusive range 0.1 through 1.  It also
accepts the standard trigger threshold, trigger time, search, boot time, and noise
adaptation options.  Silence may yield empty output; speech starts near the detected
onset.  Stereo remains stereo and detection uses the standard channel combination.
Invalid option values fail.

`dither` supports rectangular/TPDF, sloped TPDF (`-S`/`-s`), and `-f FILTER` noise
shaping.  Valid tested filter names include `lipshitz`, `f-weighted`, `modified-e-weighted`,
`improved-e-weighted`, `gesemann`, `shibata`, `low-shibata`, and `high-shibata`.
Names use SoX's case-insensitive unambiguous-prefix parsing, including hyphenated names;
invalid/ambiguous/empty names fail.  Multiple dither effects chain and produce valid
audio.  `-D` prevents automatic dither but does not disable an explicit dither effect.

## Spec 36

The remaining advertised effects exercised by the contract must be functional:
`allpass`, `band`, `biquad`, `deemph`, `riaa`, `oops`, `loudness`, `contrast`,
`hilbert`, and `tremolo` use the semantics already grouped above.  They may not be
accepted as no-ops.  Every effect emits its standard missing-argument/invalid-option
usage failure, preserves or changes metadata as documented by its signal operation,
and works in a multi-effect chain.

The `--plot` modes are an exception to normal audio production and exit-status rules:
for a supported filter they print a gnuplot or Octave transfer-response program to
stdout, write nothing to stderr, and exit 2.  Analysis effects write text to stderr
while allowing a null output.  Experimental markers in help (`divide+`, `firfit+`) and
library-only markers (`input#`, `output#`) are part of help
presentation; only command-line effects described here need executable processing.

## Spec 37

Format conversion must be deterministic under `-RD`, including the reference sample
rounding and dither suppression used for lossless round-trip vectors.  Conversions
among equal-or-greater precision signed/unsigned integer, float, DAT, AU, WAV, AIFF,
AIFC, SPH, native SOX, and supported raw forms must reproduce original bytes after a
round trip when the enclosing format is lossless and no metadata normalization makes
that impossible.  Multichannel samples stay interleaved in channel order and frame
counts do not drift.

The supported non-lossless/coercing conversions also include 44100-Hz, two-channel,
8-bit unsigned PCM to 8SVX, with the signed-encoding coercion and warning specified in
Spec 14.

For DSP comparisons, implement the actual SoX 14.4.2 algorithms, initialization,
coefficient design, latency, flushing, and rounding.  Merely producing a file with
plausible metadata is insufficient: tests inspect amplitude, RMS, extrema, frequency,
duration, per-channel values, clipping, sometimes full `stat`/`stats` text, and for
selected cases exact output bytes.

## Spec 38

An invocation with no inputs fails with `No input filenames specified` and also shows
usage.  A nonexistent input reports that it cannot be opened.  Empty/corrupt
self-describing files fail cleanly.  Unknown global options, formats, encodings, and
effects that remain selected fail; an overwritten per-file selector behaves as in
Spec 8.  An unrecognized token in the ambiguous final positional slot can instead be
treated as the output filename.  Specifically, if `PATH/x.wav` does not exist, then
`executable -n PATH/x.wav not-an-effect` treats `PATH/x.wav` as an input and
`not-an-effect` as the output, exits 2 with empty stdout, and reports:

```text
/workspace/executable FAIL formats: can't open input file `PATH/x.wav': No such file or directory
```

The diagnostic therefore does not name `not-an-effect`.  Missing output filename or
required effect arguments fail.  Failures are on stderr and do not silently produce a
successful output.

Validation occurs before unsafe arithmetic or allocation.  This includes zero rates
or channels, malformed numeric text, resampling and effect options identified as
invalid by their effect-specific requirements, truncated headers, impossible codec
constraints, and enormous header channel values.

Where SoX's contract is to warn and coerce rather than fail (format-mandated mono/rate,
XA header corrections, clipping), do that and continue with exit zero.  Partial
output cleanup and overwrite behavior must follow normal SoX 14.4.2 behavior.

## Spec 39

Observable text is locale-independent English and uses `.` as decimal separator.
Paths embedded in diagnostics are the actual argv paths.  Standard field names,
capitalization, spacing, newlines, numeric precision, and stdout/stderr selection are
part of the interface. In particular, help/version output identifies v14.4.2, full
information uses aligned SoXI labels, and `stat`/`stats` use their standard stderr
tables.

The implementation may be written in any language or may incorporate compatible
libraries, but it must be a standalone runnable `executable` from the evaluator's
perspective.  No behavior is required of a separately named `sox`, `soxi`, `play`, or
`rec` command, and no build command or repository-source behavior is assigned to the
artifact.

## Spec 40

Conformance is assessed through representative compositions, not only isolated
features.  Examples include synth→filter→gain→analysis, noiseprof→noisered,
input-combine→effects→rate conversion, encoded-format→WAV→encoded-format,
stdin→WAV stdout→stdin, and buffered multichannel processing.  Therefore state must
come from the actual input bytes and preceding operations; filenames, invocation
order, or known fixtures must not be special-cased.

Any behavior not stated in this contract is outside scope.  For behavior stated as
SoX-compatible because exact numerical or textual fidelity is required, the target is
the deterministic behavior of SoX 14.4.2 with the built-in format/effect inventory
printed in Spec 4, on a little-endian POSIX environment.
