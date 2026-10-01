# Exploring the benchmark

Everything here is optional for running the evaluations in the [README](../README.md). It covers rebuilding the benchmark and a few components that are useful to inspect or tune.

## Benchmark construction

Rebuilding the benchmark from scratch runs the full pipeline for every task: specification improvement, reference-test linking, mutant generation and repair, and specification iteration.
The command we used is:

```bash
bash scripts/construction/run_all_production.sh
```

It runs `scripts/construction/run_iterative_all_safe.sh` over `ground_truth/valid_task.txt` and writes to `output/construction` (override with `PROGRAMBENCH_TASKS_FILE` and `PROGRAMBENCH_ITER_ROOT`).
Add `--list-only` to print the command without running it.
To run selected tasks, call the runner directly:

```bash
bash scripts/construction/run_iterative_all_safe.sh --iter-root output/construction --task abishekvashok__cmatrix.5c082c6
```

### Models and reasoning effort

Every construction agent step (spec improvement, test linking, mutant generation and repair, solving, failure classification, polishing, test generation) defaults to `gpt-5.6-sol` with `high` reasoning. The defaults are registered at the top of `scripts/construction/run_iterative_all.sh`. To switch them, pass options to the runner:

```bash
# Every step
bash scripts/construction/run_iterative_all_safe.sh --iter-root output/construction --task <task> \
    --model-name gpt-5.6-luna --reasoning-effort xhigh
```

`--model-name` and `--reasoning-effort` override all steps at once. To change only some steps, edit the matching `programbench_agent_route_register STEP MODEL EFFORT` line (an optional fourth and fifth argument sets the retry model and effort for `ensure_mutants_killed`). The step names are listed under "Agent route steps" in `--help`.

### Reference-suite pruning

The reference suite is treated as fixed: tests that fail on the ground-truth implementation are kept and are not counted as mutant kills. To let mutant validation add such tests (and tests that kill over 50% of mutants) to the skip list, pass `--prune-failing-tests`.

See `bash scripts/construction/run_iterative_all_safe.sh --help` for all options. The stages are described in [iteration-pipeline.md](iteration-pipeline.md).

### Local inputs

Construction works on local copies of its inputs. Each task first fetches whatever is missing:

| Input | Local path | Source |
| --- | --- | --- |
| Reference tests | `extracted-tests/<task>/` | `eth-sri/tsb-reference_tests` |
| Ground-truth executable | `ground_truth/executable/<task>/` | `eth-sri/tsb-reference_impl` |
| Ground-truth sources | `ground_truth/implementation/<task>/` | `eth-sri/tsb-reference_impl` |
| Original workspace | `cleanroom/original/<task>/` | the task's `:task_cleanroom` Docker image |

To fetch them ahead of time, run `uv run python scripts/dataset/fetch_task_inputs.py` (all tasks in `ground_truth/valid_task.txt` by default; `--task` selects one).
It skips anything already present. Evaluation never needs these copies: it resolves `hf://` inputs itself.

## Inspecting a mutant

Each task's mutant store holds `mutants.json` (one entry per mutant: `id`, `target_spec`, `target_test`, `target_test_description`, `mutation`, and the compiled `payload`) and, for sealed stores, `sources.json`.
Sealed stores keep only the compiled executables, as compressed content-addressed blobs under `.artifacts/sha256/`, plus the source files that differ from the ground truth. That is why the HuggingFace store is small.
The sources of a mutant are therefore an overlay on `ground_truth/implementation/<task>`, and a diff against the ground truth is the natural way to see what a mutant changes.

Download the store and the ground-truth sources for a task, unpack one mutant with its sources, and diff it:

```bash
T=nachoparker__dutree.44e877d
uv run hf download eth-sri/tsb-mutants --repo-type dataset --include "$T/*" --local-dir output/mutants
uv run python scripts/dataset/fetch_task_inputs.py --task $T
uv run programbench extract-mutant output/mutants --task $T --mutant repo_49 --sources
diff -ru ground_truth/implementation/$T output/mutant-sandbox/$T/repo_49/repo_49
```

`extract-mutant` writes `executable` (the mutant binary, runnable by hand), `mutant.json` (its manifest entry, including the `mutation` description, e.g. "Spec 17: a lone malformed LS_COLORS component is silently ignored instead of panicking.") and, with `--sources`, the full source tree in a `<mutant>/` subfolder.
`--mutants-dir` is the first argument and must be a local directory. Use `--output` and `--ground-truth-dir` to change where the sandbox is written and where the ground-truth sources are read from.
Whitespace and line-ending noise can appear in the diff; add `-w` to ignore it.

Related commands:

| Command | Purpose |
| --- | --- |
| `programbench materialize-mutants <dir> --task T` | Rebuild every `repo_N` source tree of a sealed store (in place, or under `--output`) |
| `programbench seal-mutants <dir> --task T` | Collapse an unsealed store back into the compact form |
| `scripts/dataset/upload_mutant_store_to_hf.py` | Seal (if needed) and upload a store |

`ensure-mutants-killed` (`scripts/construction/ensure_mutants_killed.sh`) additionally writes `mutants.diff.patch` to its work directory: the diff of all mutant trees before and after the repair pass.

## Task images

Evaluation and agent runs use per-task Docker images named `programbench/<owner>_1776_<repo>.<hash>:<tag>` (the `__` in the instance ID becomes `_1776_`; see `image_name_from_instance_id` in `src/programbench/constants.py`; the registry organisation is `PROGRAMBENCH_DOCKER_ORG`, default `programbench`).

| Tag | Origin | Used for |
| --- | --- | --- |
| `task_cleanroom` | Pulled from the registry. The only image fetched remotely. | Base image; contains the specification workspace without the implementation |
| `task_patched` | Built locally by `scripts/docker/install_task_patched.sh` on top of `task_cleanroom` | Running generated test suites (adds generic tooling fixes and pinned pip constraints) |
| `task_cleanroom_codex` and the other agent cleanrooms | Built locally by `scripts/docker/install_agent_cleanroom.sh` (`install_codex_cleanroom.sh` for Codex) from `task_cleanroom` | Running a coding-agent CLI against the specification |
| `task_mutantbuild` | Built locally by `scripts/docker/install_task_mutantbuild.sh` on top of `task_cleanroom_codex` | Compiling mutants during construction |

The eval scripts pull `task_cleanroom` if it is missing and build the rest on first use, so nothing needs to be prepared by hand.
To prune the local images afterwards, use `scripts/docker/cleanup_programbench_docker.sh`; it keeps `task_cleanroom`, since that is the one that has to be re-downloaded (and `task_cleanroom_codex`, which the others build on). Container cleanup for a batch is described in [container-cleanup.md](container-cleanup.md).
The images are `linux/amd64` only.

## Configuration: limits and resources

| Setting | Default | Where |
| --- | --- | --- |
| Agent test-generation / implementation timeout | 21600 s each | `--test-timeout` / `--solve-timeout` of `scripts/eval/<agent>_eval.sh` (`default_test_timeout`, `default_solve_timeout`); pass through `run_agents.sh` after `--` |
| Time limit for running a test suite against one executable | 3600 s, hard-coded | `step_name="run_tests"` in `src/programbench/eval/test_suite_eval.py` |
| Time limit for a single subprocess spawned by a test | 300 s | `PROGRAMBENCH_SUBPROCESS_TIMEOUT` (`0` disables the watchdog; plugin in `src/programbench/eval/pytest_watchdog.py`) |
| Docker run / copy timeouts | 300 s | `PROGRAMBENCH_DOCKER_RUN_TIMEOUT`, `PROGRAMBENCH_DOCKER_CP_TIMEOUT` |
| Container memory and pids | 60 GB, swap 60 GB, 2048 pids | `DOCKER_RUN_ARGS` in `src/programbench/constants.py` |
| CPUs per test branch | 2 | `default` in `src/programbench/data/test_branch_cpus.json`; per-task overrides go under `tasks` |
| Parallelism | see `--workers`, `--mutant-workers`, `--branch-workers`, `--branch-cpus`, `--docker-cpus`, `--cpu-budget` | `run_agents.sh --help` and `programbench eval-tests --help` |
| Network during evaluation | none | `PROGRAMBENCH_EVAL_NETWORK` (empty for the default bridge network) |
| Network for agent containers | `pb-egress`, proxy `http://pb-proxy:3128`, API hosts only | `PROGRAMBENCH_EGRESS_NETWORK`, `PROGRAMBENCH_EGRESS_PROXY`; created by `scripts/docker/setup_egress_network.sh`, allowlist in `scripts/docker/egress-squid.conf` |
| Docker binary | `docker` | `PROGRAMBENCH_DOCKER_EXECUTABLE` |

Other timeouts are command-line options of the individual `programbench` subcommands, such as `--timeout` for `generate-tests`, `improve-spec`, `generate-mutants` and `classify-failures`.