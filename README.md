# TestSuiteBench

Can coding agents write a test suite strong enough to tell a correct program from a subtly broken one, working only from its specification?
Each task pairs a specification of a real CLI tool (from [ProgramBench](https://github.com/facebookresearch/programbench)) with the ground-truth executable and a set of mutants.
A generated test suite is scored on **validity rate** (the ground truth passes it) and **mutation score** (it kills the mutants).

> [!IMPORTANT]
> All task images are built for `linux/amd64`. Run construction and evaluation on a Linux x86_64 machine with Docker.

## Setup

```bash
uv sync
```

The final specifications are already in `ground_truth/spec/<instance_id>/spec.md`.
The reference tests, mutants, and ground-truth executables are read directly from HuggingFace ([Reference Tests](https://huggingface.co/datasets/eth-sri/tsb-reference_tests), [Mutants](https://huggingface.co/datasets/eth-sri/tsb-mutants), [Ground Truth](https://huggingface.co/datasets/eth-sri/tsb-reference_impl)): each task downloads only its own files into the HuggingFace cache when it first needs them.

Optionally, pre-download the datasets into the cache, for example before running offline with `HF_HUB_OFFLINE=1`:

```bash
uv run hf download eth-sri/tsb-reference_tests --repo-type dataset
uv run hf download eth-sri/tsb-mutants --repo-type dataset
uv run hf download eth-sri/tsb-reference_impl --repo-type dataset
```

### Agent credentials

Log in or export the credentials for the agent you want to run before launching it. Each run prints a `[codex] credentials: ...` or `[claude] credentials: ...` line naming the credential in use. Credentials are listed in order of priority, and the first one found is the only one given to the container:

| Agent | Credential, in priority order | Override |
| --- | --- | --- |
| Codex | 1. The login from `codex login` (a ChatGPT subscription), read from `~/.codex/auth.json` or `OPENAI_API_KEY`. | `PROGRAMBENCH_CODEX_AUTH_FILE` selects another login file. `PROGRAMBENCH_CODEX_AUTH=login` or `api-key` selects the source explicitly. |
| Claude Code | 1. `CLAUDE_CODE_OAUTH_TOKEN`, a long-lived token from `claude setup-token`.<br>2. `ANTHROPIC_API_KEY` or `ANTHROPIC_AUTH_TOKEN`.<br>3. The `claude` login in `~/.claude/.credentials.json`. | `PROGRAMBENCH_CLAUDE_CREDENTIALS_FILE` selects a credentials file and takes precedence over everything above. |
| OpenRouter-based models (Qwen Code, Muse, ...) | `OPENROUTER_API_KEY`, exported to the agent as an OpenAI-compatible key. | The base URL defaults to `https://openrouter.ai/api/v1`. |

```bash
codex login                         # Codex (ChatGPT subscription)
export CLAUDE_CODE_OAUTH_TOKEN=...  # Claude Code
export OPENROUTER_API_KEY=...       # OpenRouter-based models
```

## Evaluation

`scripts/eval/run_agents.sh` runs one or more model configurations (`--runs`) over a set of tasks. Agents run in Docker with network access limited to their provider's API.
The available run IDs and their harnesses are listed in [scripts/agents/README.md](scripts/agents/README.md).

### Test Generation

Generate a test suite from the specification and evaluate it against the ground truth and the mutants:

```bash
bash scripts/eval/run_agents.sh --runs "claude-opus-5 codex-gpt-5.6-sol" \
    --tasks-file ground_truth/valid_task.txt --jobs 2 -- --part test_gen
```

**Other configurations**

| Option | Description | Default | Example options |
| --- | --- | --- | --- |
| `--runs "RUN ..."` | Model configurations (run IDs) to run, all concurrently. | `codex-gpt-5.6-luna` | `claude-opus-5`, `claude-opus-5.5`, `claude-sonnet-5.5`, `codex-gpt-5.6-sol`, `codex-gpt-6-sol`, `codex-gpt-6-luna`, `codex-gpt-6.1-sol`, `codex-gpt-6-astra`, `gemini-3.8-flash`, `qwen-3.8-flash`, `deepseek-v4-flash-0423`, `glm-5.3-flash` |
| `--task TASK` | Task instance ID (repeatable). | none | any instance ID under `ground_truth/spec/` |
| `--tasks-file FILE` | File with one task instance ID per line. | none | e.g. `ground_truth/valid_task.txt` |
| `--jobs N` | Number of tasks run in parallel per configuration. | `1` | any positive integer |
| `--output-root DIR` | Root directory for `codegen/`, `testgen/`, `timings/` and `logs/`. | `output/eval` | any local path |
| `--reference-tests-dir DIR` | Reference tests. | `hf://eth-sri/tsb-reference_tests` | another revision `hf://REPO_ID@REVISION`, or a local copy |
| `--mutants-dir DIR` | Mutants. | `hf://eth-sri/tsb-mutants` | another revision `hf://REPO_ID@REVISION`, or a local copy |
| `--ground-truth-dir DIR` | Ground-truth executables. | `hf://eth-sri/tsb-reference_impl` | another revision `hf://REPO_ID@REVISION`, or a local copy |
| `--model RUN=MODEL` | Override the model of a run (repeatable). | per run ID | e.g. `--model codex-gpt-5.6-sol=gpt-5.6-luna` |
| `--reasoning RUN=EFFORT` | Override the reasoning effort of a run (repeatable). | per run ID (e.g. `medium` for Codex, `high` for Claude) | e.g. `--reasoning codex-gpt-5.6-sol=low`; also `medium`, `high`, `xhigh`, `max` where the model supports them |
| `--backend RUN=BACKEND` | Override the eval backend of a run (repeatable). | per run ID | `claude`, `codex`, `gemini`, `qwen`, `deepseek`, `glm`, `muse` |
| `--testgen-with-code` | Run only test generation, and also give the agent the ground-truth executable. | off | flag, no value |
| `--dry-run` | Print the commands without running them. | off | flag, no value |

Test suites and their evaluation results (`<instance_id>.test_eval.json`) are written to `output/eval/testgen/<model>_<reasoning>/<instance_id>/`.
To also give the agent the ground-truth executable, pass `--testgen-with-code` instead of `-- --part test_gen`; results then go to `output/eval/testgen/<model>_<reasoning>_with_code/`.

To re-evaluate existing test suites, for example ones produced by your own agent, use:

```bash
uv run programbench eval-tests \
    output/eval/testgen/<model>_<reasoning> \
    --workers 4 --mutant-workers 8
```

Each `<instance_id>/tests.tar.gz` must unpack to an `eval/run.sh` that runs the tests against `./executable` and writes JUnit XML to `eval/results.xml`.

### Code Generation

Have the agent implement the program from the same specification and evaluate it against the reference tests:

```bash
bash scripts/eval/run_agents.sh --runs "claude-opus-5 codex-gpt-5.6-sol" \
    --tasks-file ground_truth/valid_task.txt --jobs 2 -- --part exec_gen
```

Implementations and their evaluation results are written to `output/eval/codegen/<model>_<reasoning>/<instance_id>/`.
Leaving out `--part` runs both code generation and test generation.

## Repository Layout

The inner workings of the pipeline are detailed in [docs/explore.md](docs/explore.md).

## Citation

If you find our work helpful, please cite:

```bibtex
@misc{egashira2026testsuitebench,
    title={TestSuiteBench: Coding Agents Struggle to Generate Strong Test Suites from Specifications},
    author={Kazuki Egashira and Niels Mündler-Sasahara and Mark Niklas Mueller and Martin Vechev},
}
```

Please also consider citing ProgramBench, which inspired our work and forms the basis of this code base:

```bibtex
@misc{yang2026programbench,
    title={ProgramBench: Can Language Models Rebuild Programs From Scratch?},
    author={John Yang and Kilian Lieret and Jeffrey Ma and Parth Thakkar and Dmitrii Pedchenko and Sten Sootla and Emily McMilin and Pengcheng Yin and Rui Hou and Gabriel Synnaeve and Diyi Yang and Ofir Press},
    year={2026},
    eprint={2605.03546},
    archivePrefix={arXiv},
    primaryClass={cs.SE},
    url={https://arxiv.org/abs/2605.03546},
}
```

## License

This code base is derived from ProgramBench and is licensed under the terms of the license found in [LICENSE](LICENSE).
