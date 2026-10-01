# Scripts

Run every script from the repository root; they refer to each other by paths such as `scripts/docker/install_task_patched.sh`.

| Folder | Used for | Entry points |
| --- | --- | --- |
| [`dataset/`](dataset/) | Setting up the benchmark data locally and publishing it to HuggingFace | `fetch_task_inputs.py`, `upload_reference_tests_to_hf.py`, `upload_ground_truth_to_hf.py`, `upload_mutant_store_to_hf.py` |
| [`construction/`](construction/) | Building the benchmark: specification improvement, reference-test preparation, mutant generation and repair, and specification iteration | `run_all_production.sh`, `run_iterative_all_safe.sh` |
| [`eval/`](eval/) | Running coding agents on the benchmark and scoring their test suites and implementations | `run_agents.sh`, `run_agents_with_code.sh`, `summarize_agent_runs.py` |
| [`agents/`](agents/) | Harness drivers that run each coding-agent CLI in Docker, and converters from their logs to `traj.json` | called by `eval/` and `construction/`; see [agents/README.md](agents/README.md) |
| [`docker/`](docker/) | Task images, the restricted egress network, and container cleanup | `install_task_patched.sh`, `setup_egress_network.sh`, `cleanup_containers.py` |

`eval/classify_failures.sh` and `eval/classify_mutants.sh` are shared: `construction/iterate_spec.sh` also uses them to attribute evaluation failures.
