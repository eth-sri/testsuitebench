# 🧪 TestSuiteBench

🤔 Can coding agents write a test suite strong enough to tell a correct program from a subtly broken one, working only from its specification?
Each task pairs a specification of a real CLI tool (from [ProgramBench](https://github.com/facebookresearch/programbench)) with the ground-truth executable and a set of mutants.

🎯 A generated test suite is scored on **validity rate** (the ground truth passes it) and **mutation score** (it kills the mutants).

## ⚙️ Setup

> [!IMPORTANT]
> 🐳 All task images are built for `linux/amd64`. Run construction and evaluation on a Linux x86_64 machine with Docker.

```bash
uv sync
```

The final specifications are already in `ground_truth/spec/<instance_id>/spec.md`.
The reference tests, mutants, and ground-truth executables are read directly from HuggingFace ([Reference Tests](https://huggingface.co/datasets/eth-sri/tsb-reference_tests), [Mutants](https://huggingface.co/datasets/eth-sri/tsb-mutants), [Ground Truth](https://huggingface.co/datasets/eth-sri/tsb-reference_impl)): each task downloads only its own files into the HuggingFace cache when it first needs them.

Optionally, pre-download the datasets into the cache, for example before running offline with `HF_HUB_OFFLINE=1`:

```bash
# [!WARNING] This is optional and takes ~100 GB of your storage
uv run hf download eth-sri/tsb-reference_tests --repo-type dataset
uv run hf download eth-sri/tsb-mutants --repo-type dataset
uv run hf download eth-sri/tsb-reference_impl --repo-type dataset
```

### 🔑 Agent credentials

Log in or export the credentials for the agent you want to run before launching it.

```bash
codex login                         # Codex
export OPENAI_API_KEY=...           # Codex (API)
export CLAUDE_CODE_OAUTH_TOKEN=...  # Claude Code
export OPENROUTER_API_KEY=...       # OpenRouter-based models
```

| Agent | Credential |
| --- | --- |
| Codex | Read from `~/.codex/auth.json` or `OPENAI_API_KEY`. |
| Claude Code | 1. `CLAUDE_CODE_OAUTH_TOKEN`, a long-lived token from `claude setup-token`.<br>2. `ANTHROPIC_API_KEY` or `ANTHROPIC_AUTH_TOKEN`.<br>3. The `claude` login in `~/.claude/.credentials.json`. |
| OpenRouter-based models | `OPENROUTER_API_KEY`, exported to the agent as an OpenAI-compatible key. |



## 📊 Evaluation

`scripts/eval/run_agents.sh` runs one or more model configurations (`--runs`) over a set of tasks. Agents run in Docker with network access limited to their provider's API.
The available run IDs and their harnesses are listed in [scripts/agents/README.md](scripts/agents/README.md).

### 🧬 Test Generation

Generate a test suite from the specification and evaluate it against the ground truth and the mutants:

```bash
bash scripts/eval/run_agents.sh --runs "claude-opus-5 codex-gpt-5.6-sol" \
    --tasks-file ground_truth/valid_task.txt --jobs 2 -- --part test_gen

# Results are written to `output/eval/testgen/<model>_<reasoning>/<instance_id>/`
```

For all options of `run_agents.sh` (runs, tasks, parallelism, input locations, model and reasoning overrides), see [docs/config.md](docs/config.md).


```bash
uv run programbench eval-tests \
    output/eval/testgen/<model>_<reasoning> \
    --workers 4 --mutant-workers 8
```

Each `<instance_id>/tests.tar.gz` must unpack to an `eval/run.sh` that runs the tests against `./executable` and writes JUnit XML to `eval/results.xml`.

### 💻 Code Generation

Have the agent implement the program from the same specification and evaluate it against the reference tests:

```bash
bash scripts/eval/run_agents.sh --runs "claude-opus-5 codex-gpt-5.6-sol" \
    --tasks-file ground_truth/valid_task.txt --jobs 2 -- --part exec_gen

# Results are written to `output/eval/codegen/<model>_<reasoning>/<instance_id>/`
```

## 🗂️ Repository Layout

The inner workings of the pipeline are detailed in [docs/explore.md](docs/explore.md).

## 📚 Citation

🙏 If you find our work helpful, please cite:

```bibtex
@misc{egashira2026testsuitebench,
    title={TestSuiteBench: Coding Agents Struggle to Generate Strong Test Suites from Specifications},
    author={Kazuki Egashira and Niels Mündler-Sasahara and Mark Niklas Mueller and Martin Vechev},
}
```

💡 Please also consider citing ProgramBench, which inspired our work and forms the basis of this code base:

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

## 📄 License

[MIT LICENSE](LICENSE)
