#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if command -v python3 >/dev/null 2>&1; then
    python_cmd=(python3)
elif command -v uv >/dev/null 2>&1; then
    python_cmd=(uv run python)
else
    echo "python3 or uv is required" >&2
    exit 127
fi

exec "${python_cmd[@]}" "${script_dir}/solve_agent.py" --agent muse "$@"
