#!/usr/bin/env python3
"""Check Claude Code's live five-hour allowance before starting a run."""

from __future__ import annotations

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import sys
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


INSUFFICIENT = 75
USAGE_URL = "https://api.anthropic.com/api/oauth/usage?at_wall=1&skip_spend=1"
OAUTH_BETA = "oauth-2025-04-20"
CLAUDE_USER_AGENT = "claude-cli/2.1.278 (external, cli)"
USAGE_ATTEMPTS = 5


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--min-remaining-percent",
        type=float,
        default=25.0,
        help="stop when the five-hour window has less than this percentage left (default: 25)",
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="deprecated trajectory paths (the check now uses live usage)",
    )
    return parser.parse_args()


def oauth_token() -> str | None:
    selected_credentials = os.environ.get("PROGRAMBENCH_CLAUDE_CREDENTIALS_FILE")
    if not selected_credentials:
        token = os.environ.get("CLAUDE_CODE_OAUTH_TOKEN")
        if token:
            return token

    credentials_path = Path(
        selected_credentials or str(Path.home() / ".claude" / ".credentials.json")
    )
    try:
        credentials = json.loads(credentials_path.read_text())
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    oauth = credentials.get("claudeAiOauth") if isinstance(credentials, dict) else None
    token = oauth.get("accessToken") if isinstance(oauth, dict) else None
    return token if isinstance(token, str) and token else None


def reset_timestamp(value: Any) -> int | None:
    if isinstance(value, (int, float)):
        return int(value)
    if not isinstance(value, str):
        return None
    try:
        return int(datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp())
    except ValueError:
        return None


def live_five_hour_observation() -> dict[str, Any]:
    token = oauth_token()
    if token is None:
        raise RuntimeError("no Claude OAuth token is available")

    request = Request(
        USAGE_URL,
        headers={
            "Authorization": f"Bearer {token}",
            "anthropic-beta": OAUTH_BETA,
            "User-Agent": CLAUDE_USER_AGENT,
            "Content-Type": "application/json",
        },
    )
    for attempt in range(USAGE_ATTEMPTS):
        try:
            with urlopen(request, timeout=15) as response:
                payload = json.loads(response.read())
            break
        except HTTPError as error:
            transient = error.code == 429 or 500 <= error.code < 600
            if not transient or attempt == USAGE_ATTEMPTS - 1:
                raise RuntimeError(
                    f"Claude usage endpoint returned HTTP {error.code}"
                ) from error
            retry_after = error.headers.get("Retry-After")
            try:
                delay = max(1.0, min(float(retry_after), 30.0))
            except (TypeError, ValueError):
                delay = 2**attempt
            print(
                f"Claude usage endpoint returned HTTP {error.code}; retrying in {delay:g}s",
                file=sys.stderr,
            )
            time.sleep(delay)
        except (URLError, TimeoutError, OSError) as error:
            raise RuntimeError(f"Claude usage endpoint is unavailable: {error}") from error
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise RuntimeError("Claude usage endpoint returned invalid JSON") from error

    window = payload.get("five_hour") if isinstance(payload, dict) else None
    if not isinstance(window, dict):
        raise RuntimeError("Claude usage response has no five-hour window")
    utilization = window.get("utilization")
    resets_at = reset_timestamp(window.get("resets_at"))
    if not isinstance(utilization, (int, float)) or resets_at is None:
        raise RuntimeError("Claude five-hour usage response is incomplete")
    if not 0 <= float(utilization) <= 100:
        raise RuntimeError("Claude five-hour utilization is outside 0-100")
    return {"utilization_percent": float(utilization), "resets_at": resets_at}


def main() -> int:
    args = parse_args()
    if not 0 <= args.min_remaining_percent <= 100:
        print("--min-remaining-percent must be between 0 and 100", file=sys.stderr)
        return 2

    try:
        observation = live_five_hour_observation()
    except RuntimeError as error:
        print(
            f"Stopping before Claude call: cannot verify five-hour allowance: {error}",
            file=sys.stderr,
        )
        return INSUFFICIENT

    remaining = max(0.0, 100.0 - observation["utilization_percent"])
    reset = time.strftime(
        "%Y-%m-%d %H:%M:%S %Z", time.localtime(observation["resets_at"])
    )
    print(f"Claude five-hour limit: {remaining:.1f}% remaining, resets {reset}")

    if remaining <= 0 or remaining < args.min_remaining_percent:
        print(
            f"Stopping: less than the required {args.min_remaining_percent:g}% remains.",
            file=sys.stderr,
        )
        return INSUFFICIENT
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
