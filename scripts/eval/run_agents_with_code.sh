#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec bash "${script_dir}/run_agents.sh" \
    --testgen-with-code --output-root output/eval_with_code "$@"
