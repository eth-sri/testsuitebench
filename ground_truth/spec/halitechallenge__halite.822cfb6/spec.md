# Halite Game Environment Executable Specification

The required artifact is a POSIX-executable file named exactly `executable`. It is a single-command Halite game runner: options configure one game and each remaining positional argument is a complete bot launch-command string. Bot programs and command interpreters used by callers are provided by the surrounding harness and are not part of this artifact.

## Spec 1

`executable` shall run from any working directory and shall use that working directory for relative bot commands and default output files. A normal game invocation returns status 0 even if one or more bots fail, time out, emit bad moves, or cannot be launched; those are player failures, not engine failures. Invalid engine arguments or configurations return status 1 (or another nonzero status where explicitly allowed below). Output described as game output is written to standard output and flushed promptly. Successful games with ordinary bots, and configuration-validation failures such as an invalid `nplayers`, leave standard error empty; bot standard error is captured rather than forwarded. The invalid-replay-path and parser cases are the exceptions described later. In particular, quiet mode without `-o`/`--override` must print and flush each bot command before waiting for that bot, so an invocation such as `executable -q -i <directory> /bin/true` makes `/bin/true` available as its first output line immediately.

Options may occur before or after positional bot-command strings. One positional argument represents one entire shell command, even if that string contains spaces, such as `python3 /path/to/bot.py`. The interface has no subcommands.

## Spec 2

The supported options and aliases are:

- `-i DIR`, `--replaydirectory DIR`: select replay output location.
- `-s INTEGER`, `--seed INTEGER`: select the map seed.
- `-d "WIDTH HEIGHT"`, `--dimensions "WIDTH HEIGHT"`: select dimensions; both numbers are passed in one argument separated by whitespace.
- `-n N`, `--nplayers N`: generate a map accommodating `N` players while only one bot is being run.
- `-r`, `--noreplay`: disable replay generation.
- `-t`, `--timeout`: ignore bot communication time limits.
- `-o`, `--override`: interpret positional arguments as command/name pairs.
- `-q`, `--quiet`: select machine-readable output.
- `-h`, `--help`: show help and exit.
- `--version`: show the version and exit.

Short and long spellings have the same effect and may be combined in one invocation. Unless `-o` is present, every positional argument is a bot command.

## Spec 3

`-h` and `--help` return 0, write help to standard output, and write nothing to standard error. The help is headed by `USAGE:`, contains the invocation name (for example `./executable`), describes itself as `Halite Game Environment`, and documents every option and long name in Spec 2. It must describe dimensions as map dimensions, the seed as the map-generator seed, replay directory as the replay output location, `nplayers` as single-player-map configuration, `noreplay` as disabling replay generation, `timeout` as ignoring timeouts, `override` as a server-only name override, and quiet mode as machine-parsable output.

`--version` returns 0, writes nothing to standard error, and writes exactly, in order: one newline; the invocation name followed by two spaces and `version: 1.2`; and two more newlines. Thus, when the invocation name is `/workspace/executable`, the exact standard-output byte sequence is `\n/workspace/executable  version: 1.2\n\n`.

Help or version terminates without starting bots.

## Spec 4

An invocation with no bot command returns 1 and writes these two lines to standard output:

```text
Please provide the launch command string for at least one bot.
Use the --help flag for usage details.
```

A missing value for a value-taking option is a parse error. Its diagnostic must contain `PARSE ERROR`, identify the option, contain `Missing a value`, and direct the user to `--help`. A malformed dimensions value, such as `abc` or a lone number, returns 1 and reports a parse diagnostic containing `PARSE ERROR: Argument: -d (--dimensions)`, `Couldn't read argument value`, and `--help`. Parser diagnostics may be written to either output stream unless another spec requires a particular stream.

## Spec 5

`-n` accepts only integers 1 through 6. Values 0, 7, 8, and other out-of-range values return 1. After echoing the supplied bot command when one exists, standard output includes a blank line and:

```text
A map can only accommodate between 1 and 6 players.
```

Using `-n` with more than one bot command returns 1 and explains both that `Only single-player mode enables specified n-player maps` and that, when entering multiple bots, the caller must not specify `n`. Negative or nonnumeric player counts must also fail rather than start a game.

Without override mode, one through six bot commands are supported. Their player IDs are one-based in positional order. In a completed `P`-bot game, output contains one result for every ID `1..P`; ranks form the distinct set `1..P`.

## Spec 6

The dimensions argument is interpreted as `width height`. Explicit dimensions are honored for single-bot games and for ordinary compatible multiplayer sizes. This includes `3 3`, `5 5`, `10 10`, `10 20`, `15 20`, `20 10`, `22 18`, `25 25`, `30 10`, `10 30`, and `30 35`. Rectangular maps are valid. A multiplayer map generator may reduce an awkward requested dimension to obtain a symmetric layout, but emitted dimensions must remain positive and usable; common compatible dimensions such as `10 10`, `20 10`, and `10 20` remain exact. A two-bot request for `15 20` retains `20` as the second emitted dimension. For a two-bot `20 25` request, the second emitted dimension is one of `25`, `24`, or `20`.

If dimensions are omitted, choose positive dimensions automatically; each dimension is in the inclusive range 20 through 50 and quiet output reports the actual pair. The special request `0 0` likewise selects a valid automatic size rather than constructing an empty map. Games on all sizes listed above must finish within the caller's ordinary 5-to-30-second test allowance.

## Spec 7

A nonzero seed makes map construction and game processing deterministic. Repeating a game with the same dimensions, seed, bot commands, and replay setting produces the same player-result data. The actual nonzero seed is reported in replay metadata/output. Positive seeds through at least `2147483647` are accepted.

Seed `0`, and an omitted seed, request a freshly generated nonzero seed. Two consecutive invocations with `-s 0` must report different nonzero seeds. Different explicit seeds are not replaced or ignored; for example seed-specific replay names contain `-100.hlt`, `-200.hlt`, `-999.hlt`, and so on.

## Spec 8

Each bot command is launched through the platform shell with separate standard-input and standard-output pipes. Before play, send the bot exactly four newline-terminated records:

1. Its decimal player ID.
2. `width height`.
3. `width*height` decimal production values in row-major order, separated by spaces.
4. The initial map state encoding described below.

A map-state record begins with run-length pairs `count owner` describing exactly `width*height` row-major owner IDs, then has exactly `width*height` row-major strength values. Owners are 0 for neutral or a one-based player ID. Strengths are integers from 0 through 255. The engine then reads one line as the bot name.

After all available bots initialize, each turn sends every live bot one newline-terminated map-state record in the same encoding and reads one newline-terminated move record. Empty move records mean that every owned cell remains still. The engine must close or terminate bot processes when the game is over so repeated invocations do not leave children behind.

## Spec 9

A nonempty move record is whitespace-separated triples `x y direction`. Coordinates use `0 <= x < width` and `0 <= y < height`; directions are integers `0=STILL`, `1=NORTH`, `2=EAST`, `3=SOUTH`, and `4=WEST`. Edges wrap, making the board toroidal. Valid triples must be accepted, including triples that mention a cell the player does not own; ineffective moves can be ignored. A response containing nonnumeric text or otherwise not parseable as triples ejects that bot without aborting the engine.

Turns are simultaneous. An owned cell that stays still gains its production, capped at strength 255. A moving cell transfers its strength to the wrapped adjacent destination; friendly arrivals combine, capped at 255. Opposing forces resolve simultaneously by subtracting enemy strength, and ownership follows the surviving force. These rules need only expose owner/strength states in the protocol and replay, but the same deterministic update must be used for ranking and replay construction.

## Spec 10

By default, bot initialization has a long deadline of approximately 30 seconds; it must not declare a deliberately nonresponsive initialization bot dead in less than two seconds. Each ordinary turn response has a short deadline (approximately two seconds), sufficient to eject a bot that sleeps for five seconds or loops forever. `-t`/`--timeout` removes these communication deadlines.

An EOF, process crash, launch error, or turn timeout is handled as a player ejection while the game continues. The ejected player's territory becomes neutral. In normal mode, a first-turn timeout includes `Bot #1 timeout or error (Unix) 0`. A syntactically invalid first move includes `Bot sent an invalid character - ejecting from game.` An unlaunchable command is echoed and normal output contains either `timeout or error` or a platform `not found` message. None of these cases changes the engine exit status from 0.

## Spec 11

Bot names are their initialization response with the newline removed. Names may contain spaces, punctuation, and non-ASCII text and are reproduced in normal results. Names longer than 30 characters are truncated to the first 30 characters; thus `ThisIsAVeryLongBotNameThatExceedsThirtyCharactersLimit` becomes `ThisIsAVeryLongBotNameThatExce`. An empty name must not crash the engine and still produces an `Init Message received from player 1` record.

In override mode, positional arguments are pairs `bot-command override-name`. At least two pairs (four arguments) are required and the count must be even. Otherwise return 1 and print text containing `Invalid number of player parameters with override switch enabled` and `Override intended for server use only`. With valid pairs, only the command half is launched and the supplied name half replaces the bot-reported name in displays/replay. Both `-o` and `--override` are supported.

## Spec 12

Normal mode is human-readable. It echoes launch commands, reports dimensions, prints `Init Message sent to player N.` and `Init Message received from player N, NAME.` for successful initialization, prints progress records `Turn 1`, `Turn 2`, and so on, and ends with one record per player of the form:

```text
Player #N, NAME, came in rank #R and was last alive on frame #F!
```

When replay is enabled it also writes `Map seed was S` and `Opening a file at PATH`, with the latter path ending in `.hlt`. When replay is disabled, the game and ranking still occur but `Opening a file at` is absent. Normal output must be genuinely verbose (well over 200 bytes for an ordinary 10-by-10 game) and show more than five turn records where the game lasts that long.

For the exact compatibility invocation consisting of dimensions `15 15`, seed `111`, `-r`, and the single command `python3 tests/environment/ModBot.py`, standard output after trimming outer whitespace is: the command twice; `15 15`; the two initialization records for player 1 and `ModBot`; every consecutive line `Turn 1` through `Turn 139`; and finally `Player #1, ModBot, came in rank #1 and was last alive on frame #139!`. There are no intervening records.

## Spec 13

Quiet mode contains no `Init Message` or `Turn` prose. Its records, in order, are:

1. Without `-o`/`--override`, each effective bot command exactly as supplied, one per line and in player-ID order. In override mode this entire command prefix is omitted, so the first record is the dimensions in item 2; neither command halves nor override-name halves are printed there.
2. The actual `width height`.
3. If replay is enabled, `REPLAY_PATH SEED`; this record is omitted entirely with `-r`.
4. One result per player in ID order as `player_id rank last_frame_alive` (three decimal integers).
5. One line listing IDs of bots that timed out, crashed, or failed, separated by spaces and with a trailing space; a successful game uses a single-space line.
6. One line listing corresponding log filenames of the form `ID-NUMERIC_ID.log`, separated by spaces; a successful game uses a single-space line.

The final log line is not followed by an additional newline, so a successful output split at newlines ends in two entries each equal to one space. Result records are ordered by player ID, not by rank. `last_frame_alive` is the zero-based last completed frame for an ejected/eliminated player, or the terminal frame for a survivor.

## Spec 14

Ranking is based first on final territory and then, where final territory ties, on the cumulative territory integral over the game. Remaining exact ties are resolved deterministically so every player has a distinct rank. A normal game ends at its map-dependent turn limit, `floor(10*sqrt(width*height))`, or earlier when its state has reached the engine's terminal condition. A bot ejected while responding to turn 10 is last alive on frame 9; a bot ejected on its first move is last alive on frame 0.

The following deterministic compatibility results are normative:

- One `SimpleBot` that always sends empty move lines on a `10 10` map with seed 1 finishes as `Player #1, SimpleBot, came in rank #1 and was last alive on frame #100!`.
- One `ModBot` on `3 3`, seed 1, has quiet result `1 1 30`. The same result frame 30 applies on `3 3`, seed 1000, with `-n 1 -r`.
- One `ModBot` on `25 25`, seed 12345, with `-n 1 -r`, has `1 1 250`.
- One `ModBot` on `15 20`, seed 54321, with `-n 1 -r`, has `1 1 173`.
- Two `ModBot` commands on `10 10`, seed 1001, produce player 1 at rank 1 and player 2 at rank 2; both last-frame values exceed 50 and player 1's is at least player 2's.
- Two `ModBot` commands on `10 10`, seed 998, produce exactly `1 2 100` then `2 1 100`.
- A turn-10 timeout as player 1 against `ModBot` on `10 10`, seed 1001, produces `1 2 9`, player 2 at rank 1, and timeout-ID line `1`. A turn-10 crash with seed 1003 has the same player-1 result and timeout ID.
- If players 1 and 2 both fail on turn 10 and player 3 survives on `20 20`, seed 1009, players 1 and 2 both have last frame 9 and ranks `{2,3}`, player 3 has rank 1, and the failure-ID line is `1 2`.
- An invalid first move from `InvalidMoveBot` ends with `Player #1, InvalidMoveBot, came in rank #1 and was last alive on frame #0!`; a first-turn timeout from `TimeoutBot` has the analogous rank and frame 0 result.

## Spec 15

Replay generation is on by default. A default replay is written in the invocation working directory and its path in both quiet and normal output is `./ID-SEED.hlt`, where `ID` consists only of decimal digits. With an explicit nonzero seed, the basename ends exactly in `-SEED.hlt`. Exactly one replay is created per game. The quiet replay record repeats the numeric seed after the path, for example `./123456-42.hlt 42`.

`-i DIR` and `--replaydirectory DIR` place the replay at the requested location and quiet/normal output reports that path. Existing directory arguments without a trailing separator receive the `.hlt` file directly. For compatibility, when the argument ends in `/` and it contains an existing `Replays` directory, the file is placed in that `Replays` subdirectory. A nonexistent/unwritable replay location causes a nonzero exit and standard error containing `Could not open file for replay`.

`-r`/`--noreplay` creates no `.hlt` file. It also omits the replay/seed record from quiet output and omits both the opening-file message and replay path from normal output. All other game and ranking behavior remains available.

## Spec 16

Each `.hlt` replay is UTF-8 JSON, is nonempty, and for an ordinary 10-by-10 game is larger than 1000 bytes. Its top-level object contains at least:

- `version`: exactly integer 11.
- `width`, `height`: integer actual map dimensions.
- `num_players`: integer number of launched player slots.
- `num_frames`: positive integer.
- `player_names`: an array of exactly `num_players` effective names in player-ID order.
- `productions`: a `height`-element array whose rows each contain `width` integer production values.
- `frames`: an array of exactly `num_frames` frames.
- `moves`: an array of exactly `num_frames - 1` move frames.

For a single `ModBot`, `player_names` is `["ModBot"]`; for two it is `["ModBot", "ModBot"]`. Replays retain actual requested dimensions in the tested single-player cases, including `5 5` and `10 10`.

## Spec 17

Every replay frame is a `height` by `width` row-major array. Each cell is a two-element array `[owner, strength]`; owner is 0 or a valid player ID and strength is an integer from 0 through 255. In a replay for two successfully initialized players, owner 1 and owner 2 must each occur in at least one frame.

Every replay move frame is a `height` by `width` array of integer direction codes in the inclusive range 0 through 4. The frame and move counts must remain consistent even when many turns are recorded. The JSON data is the same game state sent through the bot protocol, not a different coordinate orientation.

## Spec 18

Games must remain robust across one through six bots, odd player counts, square and rectangular boards, repeated sequential runs, valid empty-move bots, bots making legal moves, bots with distinct names, and mixtures containing one crashed or unlaunchable bot. A surviving bot is still ranked and the engine returns 0. Four-player and five-player quiet results include IDs and all distinct ranks, and six-player runs include at least six three-integer statistics records. Outside override mode, the reference command strings themselves must be echoed verbatim; the implementation must not rewrite absolute paths, remove command arguments, or substitute bot names for commands in the quiet prefix. Override mode instead omits that prefix as required by Spec 13.
