from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from urllib.error import HTTPError


ROOT = Path(__file__).resolve().parents[1]


def load_checker():
    path = ROOT / "scripts" / "eval" / "check_claude_limit.py"
    spec = importlib.util.spec_from_file_location("check_claude_limit", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Response:
    def __init__(self, payload: dict):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode()


def run_main(checker, monkeypatch, capsys, payload: dict, minimum: int = 25):
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "secret-token")
    monkeypatch.setattr(checker, "urlopen", lambda _request, timeout: Response(payload))
    monkeypatch.setattr(
        checker.sys,
        "argv",
        ["check_claude_limit.py", "--min-remaining-percent", str(minimum), "."],
    )
    status = checker.main()
    return status, capsys.readouterr()


def test_live_usage_allows_when_at_least_25_percent_remains(monkeypatch, capsys):
    checker = load_checker()
    status, captured = run_main(
        checker,
        monkeypatch,
        capsys,
        {"five_hour": {"utilization": 75, "resets_at": "2099-01-01T00:00:00Z"}},
    )
    assert status == 0
    assert "25.0% remaining" in captured.out


def test_live_usage_stops_below_25_percent(monkeypatch, capsys):
    checker = load_checker()
    status, captured = run_main(
        checker,
        monkeypatch,
        capsys,
        {"five_hour": {"utilization": 75.1, "resets_at": "2099-01-01T00:00:00Z"}},
    )
    assert status == checker.INSUFFICIENT
    assert "less than the required 25%" in captured.err


def test_missing_live_usage_fails_closed(monkeypatch, capsys):
    checker = load_checker()
    status, captured = run_main(checker, monkeypatch, capsys, {})
    assert status == checker.INSUFFICIENT
    assert "cannot verify five-hour allowance" in captured.err


def test_transient_usage_throttle_is_retried(monkeypatch, capsys):
    checker = load_checker()
    responses = iter(
        [
            HTTPError(checker.USAGE_URL, 429, "throttled", {}, None),
            Response(
                {"five_hour": {"utilization": 50, "resets_at": "2099-01-01T00:00:00Z"}}
            ),
        ]
    )

    def fake_urlopen(_request, timeout):
        response = next(responses)
        if isinstance(response, Exception):
            raise response
        return response

    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "secret-token")
    monkeypatch.setattr(checker, "urlopen", fake_urlopen)
    sleeps = []
    monkeypatch.setattr(checker.time, "sleep", sleeps.append)
    monkeypatch.setattr(
        checker.sys,
        "argv",
        ["check_claude_limit.py", "--min-remaining-percent", "25", "."],
    )

    assert checker.main() == 0
    captured = capsys.readouterr()
    assert sleeps == [1]
    assert "retrying in 1s" in captured.err
    assert "50.0% remaining" in captured.out


def test_oauth_token_can_come_from_claude_credentials(tmp_path, monkeypatch):
    checker = load_checker()
    credentials = tmp_path / ".credentials.json"
    credentials.write_text(json.dumps({"claudeAiOauth": {"accessToken": "from-file"}}))
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "overrides-credentials")
    monkeypatch.setenv("PROGRAMBENCH_CLAUDE_CREDENTIALS_FILE", str(credentials))
    assert checker.oauth_token() == "from-file"
