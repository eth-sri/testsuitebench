#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."

tasks_file=${PROGRAMBENCH_TASKS_FILE:-ground_truth/valid_task.txt}
iter_root=${PROGRAMBENCH_ITER_ROOT:-output/construction}
tasks=()
while IFS= read -r line || [[ -n "$line" ]]; do
    line=${line%%#*}
    read -r task _ <<< "$line"
    [[ -z "${task}" ]] || tasks+=(--task "$task")
done < "${tasks_file}"
if (( ${#tasks[@]} == 0 )); then echo 'No enabled tasks' >&2; exit 1; fi
command=(bash scripts/construction/run_iterative_all_safe.sh \
    --iterations 0 --jobs 10 --cpu-budget 32 --mutant-build-jobs 8 \
    --target-tests-per-spec 6 --final-mutants-per-spec 3 \
    --min-num-spec-sec 10 --max-num-spec-sec 50 \
    --model-name gpt-5.6-sol --reasoning-effort high  --max-repair-attempts 3 \
    --iter-root "${iter_root}" \
    "${tasks[@]}" "$@")
for arg in "$@"; do
    if [[ "$arg" == --list-only ]]; then
        printf "%q " "${command[@]}"
        printf "\n"
        exit 0
    fi
done
exec "${command[@]}"
