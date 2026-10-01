# Evaluation options

Options of `scripts/eval/run_agents.sh`, which the evaluation sections of the [README](../README.md) use. Run `bash scripts/eval/run_agents.sh --help` for the full list.

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
