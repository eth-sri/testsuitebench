#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if command -v uv >/dev/null 2>&1; then
    python_cmd=(uv run python)
elif command -v python3 >/dev/null 2>&1; then
    python_cmd=(python3)
else
    echo "python3 or uv is required" >&2
    exit 127
fi

exec "${python_cmd[@]}" "${script_dir}/generate_tests_claude.py" "$@"
