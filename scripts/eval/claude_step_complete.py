#!/usr/bin/env python3
"""Return success when a saved Claude step completed and its artifacts exist."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trajectory", required=True, type=Path)
    parser.add_argument("--artifact", required=True, action="append", type=Path)
    args = parser.parse_args()

    if not args.trajectory.is_file() or any(not path.is_file() for path in args.artifact):
        return 1
    try:
        payload = json.loads(args.trajectory.read_text())
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return 1

    info = payload.get("info") if isinstance(payload, dict) else None
    if not isinstance(info, dict):
        return 1
    return 0 if info.get("exit_status") == "ok" and info.get("returncode") == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
