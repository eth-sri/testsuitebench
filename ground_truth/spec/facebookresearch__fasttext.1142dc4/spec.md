# fastText-compatible executable specification

The required artifact is one executable file named exactly `executable`. It implements the command-line interface, model formats, training and inference behavior described below. All text is UTF-8 unless explicitly described as binary. “Standard output” and “standard error” mean separate byte streams; a command which fails must return a nonzero status. Paths are used exactly as supplied and may be absolute or relative.

## Spec 1

`executable` is a fastText-compatible command-line program invoked as:

```text
executable <command> <arguments>
```

It supports exactly these public commands: `supervised`, `quantize`, `test`, `test-label`, `predict`, `predict-prob`, `skipgram`, `cbow`, `print-word-vectors`, `print-sentence-vectors`, `print-ngrams`, `nn`, `analogies`, and `dump`.

With no command or with an unknown command, it writes the following text to standard error, writes nothing to standard output, and fails:

```text
usage: fasttext <command> <args>

The commands supported by fasttext are:

  supervised              train a supervised classifier
  quantize                quantize a model to reduce the memory usage
  test                    evaluate a supervised classifier
  test-label              print labels with precision and recall scores
  predict                 predict most likely labels
  predict-prob            predict most likely labels with probabilities
  skipgram                train a skipgram model
  cbow                    train a cbow model
  print-word-vectors      print word vectors given a trained model
  print-sentence-vectors  print sentence vectors given a trained model
  print-ngrams            print ngrams given a trained model and word
  nn                      query for nearest neighbors
  analogies               query for analogies
  dump                    dump arguments,dictionary,input/output vectors

```

## Spec 2

The positional command usages are:

```text
usage: fasttext test <model> <test-data> [<k>] [<th>]
usage: fasttext test-label <model> <test-data> [<k>] [<th>]
usage: fasttext predict[-prob] <model> <test-data> [<k>] [<th>]
usage: fasttext print-word-vectors <model>
usage: fasttext print-sentence-vectors <model>
usage: fasttext print-ngrams <model> <word>
usage: fasttext nn <model> <k>
usage: fasttext analogies <model> <k>
usage: fasttext dump <model> <option>
```

For `test`, `test-label`, `predict`, and `predict-prob`, `k` defaults to 1 and threshold `th` defaults to 0.0. Despite showing `<k>` without square brackets in their usage banners, `nn` and `analogies` treat `k` as optional and default it to 10. When invoked with no arguments, each returns status 1, writes nothing to standard error, and writes its following complete block to standard output, including the final blank line:

```text
usage: fasttext nn <model> <k>

  <model>      model filename
  <k>          (optional; 10 by default) predict top k labels

```

```text
usage: fasttext analogies <model> <k>

  <model>      model filename
  <k>          (optional; 10 by default) predict top k labels

```

`nn` rejects a nonnumeric `k`. With the small native fixture defined in Spec 9, `k=0`, and the query `apple\n`, native `nn` writes `Query word? ` to standard output and then terminates by SIGSEGV (a subprocess return code of -11), with empty standard error. A negative value is not rejected: with `k=-2` and the same model, the query returns the two available other words and prompts again.

Wrong argument counts fail and print the relevant usage. The complete missing-argument output for `test` is the following standard-error text, including the final blank line:

```text
usage: fasttext test <model> <test-data> [<k>] [<th>]

  <model>      model filename
  <test-data>  test data filename (if -, read from stdin)
  <k>          (optional; 1 by default) predict top k labels
  <th>         (optional; 0.0 by default) probability threshold

```

The `predict` and `predict-prob` blocks use the same four descriptions and final blank line. `test-label` also uses that layout, except its test-data line is exactly `  <test-data>  test data filename`, without the stdin parenthetical.

The complete missing-argument standard-error output for `print-ngrams` is:

```text
usage: fasttext print-ngrams <model> <word>

  <model>      model filename
  <word>       word to print

```

The `print-*`, `test*`, and `predict*` usages go to standard error. The `nn`, `analogies`, and `dump` usages go to standard output. For either missing arguments or an invalid option on a valid model, `dump` returns status 1 and writes exactly this to standard output, with empty standard error:

```text
usage: fasttext dump <model> <option>

  <model>      model filename
  <option>     option from args,dict,input,output
```

## Spec 3

Training commands use flag/value arguments, except boolean switches `-saveOutput`, `-retrain`, `-qnorm`, and `-qout`, which consume no value. Every non-boolean flag requires a following value. A missing value produces an error such as `-dim is missing an argument`. A bare argument where a flag is expected fails with text containing `Provided argument without a dash`. An unknown flag fails with `Unknown argument: <name>` and training help.

`supervised -h` fails after writing help to standard error beginning with `Here is the help`. Calling any training command without both paths fails with `Empty input or output path.` followed by its help. The help groups mandatory paths, verbosity, dictionary settings, training settings, autotune settings, and quantization settings. At minimum it names every option in Spec 4 and displays its default in square brackets. `quantize -input only-one` returns status 1, writes nothing to standard output, and writes `Empty input or output path.\n\n` followed by the training-style help to standard error. That help identifies `-input` and `-output` as mandatory but contains no `usage` line; its defaults are the unsupervised defaults (`minCount` 5, `minn` 3, `maxn` 6, `lr` 0.05, and loss `ns`).

For supervised mode, the exact help body after an error is:

```text
The following arguments are mandatory:
  -input              training file path
  -output             output file path

The following arguments are optional:
  -verbose            verbosity level [2]

The following arguments for the dictionary are optional:
  -minCount           minimal number of word occurences [1]
  -minCountLabel      minimal number of label occurences [0]
  -wordNgrams         max length of word ngram [1]
  -bucket             number of buckets [2000000]
  -minn               min length of char ngram [0]
  -maxn               max length of char ngram [0]
  -t                  sampling threshold [0.0001]
  -label              labels prefix [__label__]

The following arguments for training are optional:
  -lr                 learning rate [0.1]
  -lrUpdateRate       change the rate of updates for the learning rate [100]
  -dim                size of word vectors [100]
  -ws                 size of the context window [5]
  -epoch              number of epochs [5]
  -neg                number of negatives sampled [5]
  -loss               loss function {ns, hs, softmax, one-vs-all} [softmax]
  -thread             number of threads (set to 1 to ensure reproducible results) [12]
  -pretrainedVectors  pretrained word vectors for supervised learning []
  -saveOutput         whether output params should be saved [false]
  -seed               random generator seed  [0]

The following arguments are for autotune:
  -autotune-validation            validation file to be used for evaluation
  -autotune-metric                metric objective {f1, f1:labelname} [f1]
  -autotune-predictions           number of predictions used for evaluation  [1]
  -autotune-duration              maximum duration in seconds [300]
  -autotune-modelsize             constraint model file size [] (empty = do not quantize)

The following arguments for quantization are optional:
  -cutoff             number of words and ngrams to retain [0]
  -retrain            whether embeddings are finetuned if a cutoff is applied [false]
  -qnorm              whether the norm is quantized separately [false]
  -qout               whether the classifier is quantized [false]
  -dsub               size of each sub-vector [2]
```

Prepend `Empty input or output path.\n\n` for missing required paths, or `Unknown loss: VALUE\n\n` for an invalid loss. End the help with a newline.

## Spec 4

The accepted training configuration and defaults are:

| Option | supervised default | skipgram/cbow default | Meaning |
|---|---:|---:|---|
| `-input` | required | required | UTF-8 training corpus |
| `-output` | required | required | output prefix |
| `-verbose` | 2 | 2 | progress verbosity |
| `-minCount` | 1 | 5 | minimum word frequency |
| `-minCountLabel` | 0 | 0 | minimum label frequency |
| `-wordNgrams` | 1 | 1 | maximum word-ngram length |
| `-bucket` | 2000000 | 2000000 | hashed feature buckets |
| `-minn` | 0 | 3 | shortest character ngram |
| `-maxn` | 0 | 6 | longest character ngram |
| `-t` | 0.0001 | 0.0001 | subsampling threshold |
| `-label` | `__label__` | `__label__` | label prefix |
| `-lr` | 0.1 | 0.05 | initial learning rate |
| `-lrUpdateRate` | 100 | 100 | token interval for learning-rate updates |
| `-dim` | 100 | 100 | vector dimension |
| `-ws` | 5 | 5 | context window |
| `-epoch` | 5 | 5 | epochs |
| `-neg` | 5 | 5 | negative samples |
| `-loss` | `softmax` | `ns` | objective |
| `-thread` | 12 | 12 | worker threads |
| `-pretrainedVectors` | empty | empty | text vectors used for initialization |
| `-saveOutput` | false | false | save output matrix separately |
| `-seed` | 0 | 0 | deterministic random seed |

`-loss` accepts `ns`, `hs`, `softmax`, `ova`, and the spelling `one-vs-all`; dumps canonicalize `ova` to `one-vs-all`. An invalid value emits `Unknown loss: VALUE`, lists `{ns, hs, softmax, one-vs-all}`, and fails. Valid numeric variants exercised by the interface include dimensions 5, 8, 10, 12, 15, 17, 20, 50, 100, and 300; epochs including 0; windows 2, 3, and 10; negative counts 5, 10, and 25; buckets 100 through 100000; and one or two threads.

## Spec 5

Input tokenization is whitespace-delimited, case-sensitive, and UTF-8 preserving. Space, tab, vertical tab, carriage return, form feed, and newline delimit tokens. Newline also terminates a training example/sentence and contributes the special dictionary word `</s>`. Empty lines contain no ordinary words. Physical lines containing 1,000 tokens must not be truncated before their final tokens.

A token beginning with the configured label prefix is a label in supervised data; all other tokens are words. Multiple labels on one line are all retained. Labels need no separator beyond ordinary token boundaries: `__label__positive` is one valid token. The custom prefix from `-label`, such as `__class__`, completely replaces the default prefix. Dictionary entries retain exact spelling, punctuation, emoji, and non-ASCII bytes.

Word and label counts are corpus occurrence counts. Filter words below `minCount` and labels below `minCountLabel`. `</s>` is a word for this filtering rule, not an unconditional exception: its count is the number of contributing newlines, and it is retained only when that count reaches `minCount`. Thus a corpus can contain physical lines yet still have an empty post-filter vocabulary. Dictionary order is deterministic: words precede labels and higher counts precede lower counts, with the native dictionary/hash ordering used to resolve ties. Identical input and seed must yield identical word ordering.

## Spec 6

`supervised` learns a classifier from each line's labels and text. Its hidden representation is the mean of that line's input features: retained word IDs, each word's configured character-subword IDs, and hashed word ngrams up to `wordNgrams`. For the token sequence, first calculate each token's 32-bit FNV-1a hash as in Spec 7, reinterpret that result as a signed 32-bit integer, and sign-extend it when promoting it into the 64-bit word-ngram recurrence. A word-ngram hash starts from that promoted first-token value and uses modulo-2^64 wraparound for `hash = hash * 116049371 + promoted_next_token_hash`; bucket rows are `number_of_words + hash % bucket`. For the sequence `a b </s>` and bucket 101, this selects bucket offsets 28 for `a b` and 18 for `b </s>` (not 96 and 86).

The output objective is selected by `-loss`: full softmax, hierarchical softmax, negative sampling, or independent one-vs-all sigmoids. Training is stochastic gradient descent with learning rate decaying linearly from `lr` toward zero according to processed-token progress and `lrUpdateRate`. Output weights begin at zero and input weights are seeded uniformly in `[-1/dim, +1/dim]` using a `minstd_rand` generator seeded by worker number plus `seed`. Hierarchical softmax uses a frequency-built Huffman tree; negative sampling uses the word/label count distribution raised to power 0.5. For non-OVA supervised objectives, choose one of a line's labels uniformly per update; OVA updates every label as a positive or negative target.

Native numerical compatibility uses binary32 vectors and matrices. Logistic training uses a 513-entry sigmoid table for the interval `[-8,8]`: entry `i` is `1/(1+exp(-(16*i/512-8)))`; values outside the interval clamp to 0 or 1 and interior lookup uses the floored scaled index. Its 513-entry log table has entry `i = log((i+0.00001)/512)` and lookup index `floor(x*512)` (with x above 1 mapped to 0). Softmax itself subtracts the maximum logit, exponentiates, and normalizes directly; the prediction interface applies the additional score conversion specified in Spec 11. The hidden vector is an average of input rows; back-propagated supervised input gradients are additionally divided by the input feature count.

The implementation must actually learn: on balanced positive/negative corpora whose class-specific vocabularies are disjoint, class-specific input must predict the corresponding class when training succeeds. Some concrete supported-loss invocations instead encounter native numerical failures before producing a usable model. Softmax training on the six-line corpus formed by repeating `__label__a alpha alpha\n__label__b beta beta\n` three times, with `-dim 5 -epoch 3 -thread 1 -bucket 20 -verbose 0`, terminates by SIGABRT and leaves a zero-byte `.bin`.

There are three further exact failure cases:

- Default-softmax training on the 100-line corpus formed by 50 lines `__label__positive sunshine warm bright posN\n` for N from 0 through 49 followed by 50 lines `__label__negative storm cold dark negN\n` for N from 0 through 49, with `-dim 10 -epoch 5 -thread 1 -bucket 100 -minCount 1 -verbose 0`.
- Softmax training on the 80-line corpus formed by concatenating `__label__a common alpha tokenN\n__label__b common beta itemN\n` for N from 0 through 39, with `-dim 8 -epoch 2 -thread 1 -bucket 1000 -wordNgrams 2 -minCount 1 -verbose 0`.
- For each loss value `hs`, `ns`, and `one-vs-all`, training on the 16-line corpus formed by eight copies of `__label__a alpha red\n` followed by eight copies of `__label__b beta blue\n`, with `-dim 8 -epoch 10 -bucket 100 -thread 1 -verbose 0` and the corresponding `-loss` value.

Each of these further invocations terminates by SIGABRT (subprocess return code -6), writes nothing to standard output, and writes exactly the following to standard error:

```text
terminate called after throwing an instance of 'fasttext::DenseMatrix::EncounteredNaNError'
  what():  Encountered NaN.
```

Each leaves an existing zero-byte `<output>.bin` and does not create `<output>.vec`. The six-line failure writes the same two-line diagnostic. A one-line or one-label dataset is valid. A supervised corpus with zero recognized labels must not crash and must report `Number of labels: 0`.

## Spec 7

`skipgram` learns each context word from a center word within a randomly selected window no larger than `ws`; `cbow` learns the center word from the mean of surrounding context features. Both use the selected `ns` or `hs` objective, token subsampling controlled by `t`, line boundaries, and the same linear learning-rate schedule. When at least one dictionary word survives `minCount`, they create useful finite vectors even for repetitive corpora and corpora made of single-word lines. Skipgram and CBOW model types are distinct (`sg` and `cbow`).

When character subwords are enabled, wrap a word in boundary markers `<` and `>`, enumerate UTF-8-character ngrams of lengths `minn` through `maxn`, and hash them into `bucket` rows. Do not emit a boundary marker alone. Use 32-bit FNV-1a beginning at 2166136261, xor each signed input byte converted to 32 bits, then multiply by 16777619 with 32-bit wraparound. A retained dictionary word's feature list begins with its word row and then its subwords. Hashed subword IDs can also be enumerated for an out-of-vocabulary spelling, but native `print-word-vectors` does not use them, as specified in Spec 14. On successful training, enabling subwords must add stored input rows and therefore make an otherwise equivalent `.bin` model larger.

The following epoch-zero unsupervised invocations have no word whose count reaches the default `minCount` of 5; subword configuration does not rescue the filtered vocabulary:

- Both `skipgram` and `cbow` on `alpha beta gamma\nbeta gamma delta\n`, with `-dim 10 -bucket 10000 -minn 3 -maxn 6 -thread 1 -verbose 0`.
- `skipgram` on `king queen running walked\n`, with `-dim 10 -bucket 100 -thread 1 -verbose 0` and either `-minn 0 -maxn 0` or `-minn 2 -maxn 2`.
- `skipgram` on `king queen\n`, with `-bucket 100 -thread 1 -verbose 0` and either `-dim 5 -minn 2 -maxn 2` or `-dim 8 -minn 3 -maxn 6`.
- `cbow` on `alpha beta\nbeta gamma\n`, with `-dim 5 -bucket 100 -minn 0 -maxn 0 -thread 1 -verbose 0`.

Each terminates by SIGABRT (subprocess return code -6), writes nothing to standard output, writes the following to standard error, leaves a zero-byte `<output>.bin`, and does not create `<output>.vec`:

```text
terminate called after throwing an instance of 'std::invalid_argument'
  what():  Empty vocabulary. Try a smaller -minCount value.
```

## Spec 8

Successful `supervised`, `skipgram`, and `cbow` training writes `<output>.bin` and `<output>.vec`, replacing existing files rather than appending. Both are nonempty and distinct. Failure to open `<output>.bin` terminates by SIGABRT, writes nothing to standard output, and writes exactly the following to standard error, with no preceding training diagnostics:

```text
terminate called after throwing an instance of 'std::invalid_argument'
  what():  <output>.bin cannot be opened for saving.
```

`-saveOutput` additionally writes a nonempty `<output>.output` text matrix. For a supervised model its first line is `ROWS COLS`; each of the following ROWS lines is the corresponding label token, one space, exactly COLS numeric components separated by spaces, a trailing space, and newline. Thus an epoch-zero, two-label, five-dimensional output begins `2 5` and has rows such as `__label__a 0 0 0 0 0 `.

`<output>.vec` is human-readable UTF-8. Its first line is `W D`, where `W` is exactly the number of following word-vector rows and `D` is `dim`. Each following line is the word, one space, and exactly `D` finite parseable decimal floats. Labels are excluded. Preserve Unicode word bytes. Vector components use five significant digits and include a decimal representation with sufficient precision for ordinary nonzero values. Larger dimensions and vocabularies must result in larger binary models; a 100-dimensional model with the same data must be over five times the size of a 5-dimensional one. A small skipgram/CBOW model using dimension 10 and bucket 10000 must remain between 1,000 and 10,000,000 bytes, and a supervised model with bucket 1000 must remain below 1,000,000 bytes.

`-pretrainedVectors FILE` reads a text header `W D` and W `word` plus D-float rows, requires D to equal `-dim`, adds those words to the training dictionary before final thresholding, randomly initializes the whole input matrix, then replaces matching retained word rows with the supplied vectors.

## Spec 9

`.bin` is the native binary persistence format and not JSON, XML, or renamed text; more than 20% of its bytes must be outside printable ASCII. It begins with little-endian signed 32-bit magic `793712314` and version `12`. Native scalar layout is little-endian. After the header it serializes, in this order:

1. model arguments: signed 32-bit `dim, ws, epoch, minCount, neg, wordNgrams, loss, model, bucket, minn, maxn, lrUpdateRate`, then 64-bit IEEE `t`;
2. dictionary header: signed 32-bit total entry count, word count, label count; signed 64-bit token count and prune-map size, using -1 as the prune-map-size sentinel for an unpruned dictionary; each entry as NUL-terminated UTF-8 bytes, signed 64-bit count, and one byte type (`0` word, `1` label); then prune-map pairs of signed 32-bit integers when present;
3. one-byte quantized-input flag followed by either an ordinary input matrix or a quantized matrix;
4. one-byte quantized-output flag followed by either an ordinary output matrix or a quantized matrix.

An ordinary matrix is signed 64-bit row and column counts followed row-major by IEEE binary32 elements. Loss enum values are hierarchical-softmax 1, negative-sampling 2, softmax 3, and one-vs-all 4. Model enum values are CBOW 1, skipgram 2, and supervised 3. The loader must accept and reproduce results from any valid version-12 native model supplied to it, including supervised, skipgram, CBOW, and quantized models—not only files produced during its own process.

Concrete edge cases below use a small native fixture with dimension 2, supervised model enum 3, softmax loss enum 3, bucket 0, `minn=0`, `maxn=0`, and `wordNgrams=1`. Its words are `apple`, `banana`, and `</s>` with counts 20, 10, and 4 and input rows `(2,0)`, `(-2,0)`, and `(0,0)`; its labels are `__label__pos` and `__label__neg`, each with count 2 and output rows `(2,0)` and `(-2,0)`.

## Spec 10

Model loading validates existence, magic, and enough of the serialized prefix to perform the requested operation, but does not validate every version/truncation case before using the data. A missing model fails with exactly:

```text
terminate called after throwing an instance of 'std::invalid_argument'
  what():  PATH cannot be opened for loading!
```

A file that exists but is empty, is a `.vec` text file, or has the wrong magic fails with the same two-line form except the second line is `  what():  PATH has wrong file format!`; no prediction or vector output is written for those rejected files. A magic-correct file consisting of version 11 followed by the four bytes `junk` is not rejected as a wrong-format header: prediction terminates by SIGFPE (subprocess return code -8), with empty standard output and standard error. Removing the final seven bytes from the small native fixture defined in Spec 9 is likewise not detected; `predict` on an `apple` line returns status 0 and writes `__label__pos\n`. Saved models preserve vocabulary, input/output weights, model type, loss, dimension, epoch, character-ngram bounds, and wordNgrams. They preserve the configured bucket when hashed features are in use; when `wordNgrams=1` and character ngrams are disabled (`minn=0,maxn=0`), supervised training canonicalizes the unused saved bucket to 0. Repeated loads produce bit-identical formatted predictions. A second training operation at the same prefix fully overwrites the old model.

## Spec 11

`predict MODEL INPUT [k [threshold]]` loads a supervised model and emits one output line per input line. `INPUT` may be a file or `-` for standard input. Labels already present in a line are ignored as text features. Compute model scores using the saved loss, discard scores strictly below the threshold, sort descending (using the larger label index first as the deterministic tie-break), and return no more than `min(k, number_of_labels)` unique labels. The output line is the selected labels separated by one space, with no probabilities, followed by newline. If none pass the threshold, emit an empty line.

`predict-prob` performs the same operation but emits alternating label and reported-score tokens: `LABEL SCORE [LABEL SCORE ...]`. Use default stream formatting with six significant digits. For full softmax, if the directly normalized probability is `p`, ranking and display use `p + 0.00001` (implemented through the native log-score conversion), but thresholding compares the unadjusted `p` to the requested threshold. Consequently reported full-softmax scores are in `[0.00001,1.00001]` and sum to `1 + 0.00001 * number_of_labels` when every label is returned. In a two-label model, logits separated by 8000 therefore print `__label__pos 1.00001 __label__neg 1e-05`. Equal zero logits have reported score 0.50001, pass threshold 0.5, and are emitted in descending label-index order; for dictionary labels `__label__pos` then `__label__neg`, the output is `__label__neg 0.50001 __label__pos 0.50001`. At thresholds 0.50001 and 0.50002, neither equal-logit label passes and `predict` emits just the empty output line. `k` larger than the label count returns all labels. Threshold zero filters nothing.

Empty input (immediate EOF) emits nothing. An empty physical line between nonempty lines is nevertheless processed and emits a prediction for the empty feature vector. A final terminating newline does not create an additional phantom example. Plain unlabeled text is valid.

## Spec 12

`test MODEL DATA [k [threshold]]` evaluates known labels in `DATA` using the same top-k prediction and threshold rules. It writes exactly three tab-separated lines:

```text
N	EXAMPLES
P@K	PRECISION
R@K	RECALL
```

`EXAMPLES` counts lines having at least one label known to the model and at least one input feature. `correct` is the total intersection size between predicted and gold labels over counted lines; precision is `correct / number_of_returned_predictions`, and recall is `correct / number_of_known_gold_labels`. Display metrics with three significant digits, so exact 1 may appear as `1` and one third as `0.333`. When no known labeled examples/predictions exist, output `N\t0\nP@K\tnan\nR@K\tnan\n`. Thus a file containing only labels absent from the model yields N=0.

A deliberate native-interface limitation must be preserved: when `DATA` is `-`, consume standard input but report the zero-example/nan result even if labeled lines were supplied. A genuinely empty file also reports the zero-example result.

## Spec 13

`test-label` first prints one line for every model label, in dictionary label order, then prints the same three aggregate lines as `test`. Each label line is:

```text
F1-Score : FFFFFF  Precision : PPPPPP  Recall : RRRRRR   LABEL
```

Defined values use fixed six decimal places. Precision is true positives divided by predictions for the label; recall is true positives divided by gold occurrences; when both are defined, F1 is their harmonic mean. Undefined precision or recall is represented by `--------`. With the Spec 9 fixture, data `__label__pos apple\n`, and `k=2`, the absent-gold label has zero true positives and undefined recall, but its F1 is zero rather than undefined: its line is exactly `F1-Score : 0.000000  Precision : 0.000000  Recall : --------   __label__neg`. All labels appear even with no match. Custom `k` and threshold affect both per-label and aggregate metrics; aggregate headings must use that k (`P@2`, `R@2`, etc.). Because fixed formatting remains active, the aggregate values printed by `test-label` use fixed three decimal places (for example `P@1\t1.000`), unlike plain `test`.

## Spec 14

`print-word-vectors MODEL` reads whitespace-separated query words from standard input and preserves their order, producing one line per word:

```text
WORD v1 v2 ... vD 
```

The trailing space before newline is permitted and is used by native output. For a known word, its word vector is the arithmetic mean of its saved word-row and saved character-subword rows. For an OOV word, native `print-word-vectors` outputs D zeros; it does not average hashed character-subword rows even when the configured `minn` and `maxn` bounds produce usable subwords. For example, train `skipgram` at epoch zero on `king queen running walked\nking queen running\n` with `-minCount 1 -dim 5 -bucket 100 -minn 2 -maxn 2 -thread 1 -verbose 0`. Although the OOV query `kings` has two-character subwords and overlaps retained `king`, its complete output is `kings 0 0 0 0 0 ` followed by newline. Do not normalize vectors. Empty standard input succeeds with no output. This command works for unsupervised and supervised `.bin` models and native `.ftz` models.

## Spec 15

`print-sentence-vectors MODEL` reads physical lines and writes one vector-only line of D floats for each. For an unsupervised model, obtain each word vector, L2-normalize each nonzero word vector separately, sum those normalized vectors, and divide by the number of words with nonzero norm. For a supervised model, use the mean hidden line representation over its input features. An empty line produces exactly D zeros. Unknown-only sentences may likewise be zero. Input line order and count are preserved.

## Spec 16

`print-ngrams MODEL WORD` writes one line for the full word followed by character-ngram lines in generation order. Every line has the displayed token followed by exactly D floats. The character-ngram lines expose their bucket rows, but the full-word line does not reliably expose the saved word row: native output reads process-dependent invalid data for part of that row. Repeated invocations on the same `king` model have produced first components `-0.067216`, `1.111e+13`, `-7.4924e+27`, `6.1237e+23`, and `2.7282e+26`, while `print-word-vectors` consistently produced a first component of `-0.032724`. Therefore averaging the displayed `print-ngrams` rows is not the contract for `print-word-vectors`. For a model trained with `minn=2,maxn=2`, `king` includes `<k`, `ki`, `in`, `ng`, and `g>` after the full-word line. Boundary markers are visible. Models with `minn=3,maxn=6` produce the corresponding range and therefore more than five entries for `running`.

## Spec 17

`nn MODEL [k]` writes `Query word? ` immediately, then reads query words until EOF. For each query it computes its word vector, L2-normalizes it, and calculates cosine similarity against every retained dictionary word's normalized word vector. Exclude the exact query word when it is in vocabulary, select the highest k candidates, and print each as `WORD SCORE\n` in nonincreasing score order with six significant digits. OOV queries are supported through subwords and still return k results when enough vocabulary exists. After every processed query, including the last before EOF, write the prompt again. Consequently three newline-terminated queries produce four occurrences of `Query word?`.

## Spec 18

`analogies MODEL [k]` begins with `Loading model MODEL\n`, echoing the path string exactly, precomputes normalized vocabulary vectors, then repeatedly writes `Query triplet (A - B + C)? ` and reads three words. L2-normalize each of the three word vectors separately, form `normalized(A) - normalized(B) + normalized(C)`, and rank using cosine similarity (divide the dot product by the norm of this combined query). Exclude A, B, and C and print up to k unique `WORD SCORE` lines in descending score order. Scores are finite and in `[-1,1]`. Keep prompting until externally terminated; the native loop continues even after EOF. All output is flushed promptly so an interactive caller can observe it.

## Spec 19

`dump MODEL args` writes these fields, one per line and in this order:

```text
dim VALUE
ws VALUE
epoch VALUE
minCount VALUE
neg VALUE
wordNgrams VALUE
loss VALUE
model VALUE
bucket VALUE
minn VALUE
maxn VALUE
lrUpdateRate VALUE
t VALUE
```

Model names are `sup`, `sg`, and `cbow`; loss names are `hs`, `ns`, `softmax`, and `one-vs-all`. Values are the saved configuration after native canonicalization. In particular, supervised training with explicit `-bucket 10`, default `wordNgrams=1`, and `minn=0,maxn=0` dumps `bucket 0` because no hashed feature uses the bucket. For example, a supervised model trained with `-dim 100 -epoch 10 -loss hs` reports `dim 100`, `epoch 10`, `loss hs`, and `model sup`. Quantization preserves this output.

## Spec 20

`dump MODEL dict` writes total dictionary entry count on its first line, followed by every word and label as `TOKEN COUNT TYPE`, where type is `word` or `label`. The count equals the number of entry lines. `</s>` appears as a positive-count word. Custom-prefix labels appear unchanged.

`dump MODEL input` writes `ROWS COLS` then every ordinary input-matrix row as COLS floats. For models without hashed features, ROWS equals dictionary word count; generally it is the actual serialized matrix row count. `dump MODEL output` uses the same representation; for supervised softmax/negative-sampling/one-vs-all models, its row count equals label count. Columns equal `dim`. Ordinary binary models support all four dump modes.

For a quantized model, `args` and `dict` remain supported. `input` or `output` prints `Not supported for quantized models.` to standard error and returns success.

## Spec 21

`quantize -input TRAINING_DATA -output PREFIX [options]` loads `PREFIX.bin`; `-input` is the corpus available for optional retraining. Quantization is supported only for supervised models. Reject another model type, create no `.ftz`, and report `For now we only support quantization of supervised models`. On success, preserve `PREFIX.bin` byte-for-byte and create a separate, loadable `PREFIX.ftz` that supports prediction, testing, args dump, and dictionary dump.

Accepted options are `-cutoff N`, `-retrain`, `-qnorm`, `-qout`, `-dsub N`, plus applicable training options such as `-epoch` and `-verbose`. `cutoff > 0` retains the most important/frequent input words and ngrams, remaps feature IDs, and reduces the dictionary/matrix; a cutoff of 300 results in no more than about 305 dictionary entries and fewer than before. With `-retrain`, train the pruned model again on `-input` before compression. For a quantizable input matrix having at least 256 rows, different valid `dsub` values 1, 2, and 4 must alter the encoded size. `qnorm` separately quantizes row norms. `qout` quantizes the classifier only when its output matrix has at least 256 rows; otherwise fail with `Matrix too small for quantization, must have at least 256 rows`.

Ordinary input-matrix quantization also requires at least 256 source matrix rows, independently of `dsub` and independently of whether `qout` is requested. If the input matrix has fewer than 256 rows, `quantize` terminates by SIGABRT (subprocess return code -6), writes nothing to standard output, writes exactly the following to standard error, leaves the existing `.bin` unchanged, and creates no `.ftz`:

```text
terminate called after throwing an instance of 'std::invalid_argument'
  what():  Matrix too small for quantization, must have at least 256 rows
```

Concretely, this occurs after successful epoch-zero supervised training on `__label__a café 😀 common\n__label__b tea common\n__label__a __label__b shared\n` with `-dim 5 -bucket 100 -thread 1 -verbose 0 -saveOutput`; quantization fails in this way with the default `dsub` and with each explicit `-dsub` value 1, 2, and 4. Therefore this small fixture cannot produce the quantized model needed to exercise the quantized-matrix dump behavior from Spec 20.

The 256-row quantization threshold does not guarantee that every corpus capable of declaring 256 labels can first be trained. A corpus containing exactly the 256 singleton lines `__label__lN shared tokenN` for N from 0 through 255, trained with `-dim 8 -epoch 1 -thread 1 -bucket 1000 -minn 0 -maxn 0 -verbose 0`, terminates during supervised training by SIGABRT with:

```text
terminate called after throwing an instance of 'fasttext::DenseMatrix::EncounteredNaNError'
  what():  Encountered NaN.
```

It leaves a zero-byte `<output>.bin` and never reaches `quantize -qout`.

Likewise, the 80-line softmax corpus and options identified in Spec 6 terminate during the prerequisite `supervised` command with return code -6 and that same exact NaN diagnostic, leaving a zero-byte `.bin` and no `.vec`. Consequently quantization cannot be reached from that attempted source model.

For ordinary realistic models whose prerequisite supervised training succeeds, `.ftz` is nontrivial (over 1,000 bytes), smaller than `.bin`, and retains reasonable predictions and evaluation behavior.

## Spec 22

Native `.ftz` compatibility uses the same header, arguments, and dictionary layout as Spec 9. A quantized matrix serializes: a one-byte `qnorm` flag; signed 64-bit row and column counts; a signed 32-bit code byte count; that many code bytes; then its product quantizer. If `qnorm` is true, it then serializes one norm code per row and a second product quantizer for norms. A product quantizer serializes signed 32-bit dimension, number of subquantizers, regular subvector width, and final subvector width, followed by its row-major binary32 centroid table. There are 256 centroids per subquantizer. Reconstruct a row by selecting each subquantizer's centroid using its code byte and concatenating the selected subvectors; multiply by the separately decoded norm when present. Predictions and vector queries operate on these reconstructed values.

Product quantization is entered only when the matrix has at least 256 rows. It learns 256-centroid k-means codebooks per subspace; when an eligible matrix has at least 256 total rows but fewer than 256 distinct row values, values may repeat during centroid initialization. It assigns each row to its nearest squared-Euclidean centroid and stores one byte per subspace. `dsub` controls regular subspace width. The resulting format must interoperate with supplied native version-12 `.ftz` files.

## Spec 23

Supervised training enters autotune mode when `-autotune-validation FILE` is supplied. It accepts:

- `-autotune-duration` seconds, default 300;
- `-autotune-predictions` k, default 1;
- `-autotune-metric`, accepting `f1` and `f1:LABEL`;
- `-autotune-modelsize`, an optional model-size constraint string.

It searches hyperparameter configurations within the duration, evaluates the requested validation metric, and writes a usable supervised model unless final training or requested quantization fails. A valid label-specific metric such as `f1:__label__pos` succeeds. A syntactically valid model-size constraint can still fail during final quantization: on a small two-label corpus, `-autotune-modelsize 100K -dim 8 -epoch 2 -minCount 1 -bucket 1000 -thread 1 -verbose 2` terminates by SIGABRT with the native invalid-argument wrapper whose `what()` text is `Matrix too small for quantization, must have at least 256 rows`, and leaves a zero-byte `.ftz` rather than a usable model. Unknown metric syntax fails with `Unknown metric` and includes the supplied value. A missing validation file fails with `Validation file cannot be opened!`. A zero duration terminates by SIGABRT and writes exactly:

```text
terminate called after throwing an instance of 'std::runtime_error'
  what():  Didn't have enough time to train once: please increase `autotune-duration`.
```

Invalid model-size text such as `invalid_size` fails with `Unable to parse model size invalid_size`.

## Spec 24

At verbosity 2 autotune writes `Progress: P%` and `ETA: Hh Mm Ss` fields to standard error. Emit at least five progress samples for a normal eight-second run. Search progress never decreases, starts at no more than 20%, and finishes at least 95%; ETA does not materially increase, begins no higher than 20 seconds for an eight-second duration, and ends at no more than three seconds.

Any ordinary hyperparameter explicitly present on the command line is excluded from tuning and causes this exact warning on standard error:

```text
Warning : NAME is manually set to a specific value. It will not be automatically optimized.
```

This applies at least to `dim`, `lr`, and `epoch`. Autotune with a two-second duration and manually fixed dimension, epoch, thread, and minCount must still complete promptly and create `.bin` and `.vec` files.

## Spec 25

At normal verbosity, training diagnostics go only to standard error. After dictionary construction, include:

```text
Read 0M words
Number of words:  W
Number of labels: L
```

Training progress includes `Progress:`, `words/sec/thread:`, `lr:`, `avg.loss:`, and `ETA:`, reaches `100.0%` on positive-epoch successful runs, and reports label count 0 for unsupervised training. Verbosity 0 may suppress these diagnostics. Epoch zero is valid and, when dictionary construction leaves a nonempty vocabulary, completes immediately and still creates its model artifacts. At verbosity 2 its diagnostics use carriage returns before `Read` and `Progress`; replacing those carriage returns with newlines produces a blank line between the label-count line and progress. Its complete final progress record is `\rProgress: 100.0% words/sec/thread:       0 lr:  0.000000 avg.loss:      -nan ETA:   0h 0m 0s\n`.

An empty training file constructs zero words and labels, then fails with:

```text
terminate called after throwing an instance of 'std::invalid_argument'
  what():  Empty vocabulary. Try a smaller -minCount value.
```

A whitespace-only corpus is subject to the same `minCount` rule as any other corpus. In particular, `skipgram` on the two-line byte sequence `   \n\t\n`, with `-epoch 0 -dim 5 -bucket 10 -minn 0 -maxn 0 -thread 1 -verbose 2`, terminates by SIGABRT (subprocess return code -6), writes nothing to standard output, leaves a zero-byte `<output>.bin`, does not create `<output>.vec`, and writes exactly `\rRead 0M words\nNumber of words:  0\nNumber of labels: 0\nterminate called after throwing an instance of 'std::invalid_argument'\n  what():  Empty vocabulary. Try a smaller -minCount value.\n` to standard error. By contrast, five whitespace-only physical lines meet the default `minCount`: the dictionary contains the single entry `</s>` with count 5 and epoch-zero training succeeds. Blank lines interspersed with valid data do not prevent normal training.

## Spec 26

File failures are distinguished as follows. A missing training corpus reports `PATH cannot be opened for training!` in the two-line invalid-argument form from Spec 10. A missing prediction input file reports exactly `Input file cannot be opened!\n`. A missing evaluation file reports exactly `Test file cannot be opened!\n`. A missing quantization source model fails before creating `.ftz` and reports that the corresponding `.bin` cannot be opened for loading. Errors do not emit misleading prediction/evaluation output.

The implementation must safely handle Unicode and emoji, empty files and standard input, blank lines, one-example supervised datasets, 20 labels and 200+ vocabulary words, 1,000 unique-token long lines, dimensions through 300, and repeated model loads, subject to the documented empty-vocabulary failures when no word reaches `minCount`. It must finish the small training workloads in tens of seconds, avoid deadlocks with `-thread 2`, avoid multi-gigabyte output for explicitly small buckets, and must not segfault or abort merely because supervised data contains no labels. `nn` nonpositive-k behavior is the native behavior specified in Spec 2, including its `k=0` SIGSEGV.
