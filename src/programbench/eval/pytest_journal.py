# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

"""Crash-tolerant per-test journal injected into reference pytest suites."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

_JOURNAL_VALUE = os.environ.get("PROGRAMBENCH_PYTEST_JOURNAL", "")
_COMPLETED_VALUE = os.environ.get("PROGRAMBENCH_PYTEST_COMPLETED", "")
_JOURNAL_PATH = Path(_JOURNAL_VALUE) if _JOURNAL_VALUE else None
_COMPLETED_PATH = Path(_COMPLETED_VALUE) if _COMPLETED_VALUE else None
_IS_CONTROLLER = True
_REPORTS: dict[str, dict[str, Any]] = {}


def pytest_configure(config: Any) -> None:
    global _IS_CONTROLLER
    _IS_CONTROLLER = not hasattr(config, "workerinput")
    if _IS_CONTROLLER and _JOURNAL_PATH is not None:
        _JOURNAL_PATH.parent.mkdir(parents=True, exist_ok=True)
        _JOURNAL_PATH.touch()


def pytest_collection_modifyitems(config: Any, items: list[Any]) -> None:
    if _COMPLETED_PATH is None or not _COMPLETED_PATH.is_file():
        return
    try:
        completed = set(json.loads(_COMPLETED_PATH.read_text()))
    except (OSError, ValueError, TypeError):
        return
    selected = []
    deselected = []
    for item in items:
        (deselected if item.nodeid in completed else selected).append(item)
    if deselected:
        items[:] = selected
        config.hook.pytest_deselected(items=deselected)


def pytest_runtest_logreport(report: Any) -> None:
    if not _IS_CONTROLLER or _JOURNAL_PATH is None:
        return
    state = _REPORTS.setdefault(report.nodeid, {})
    if report.when == "setup":
        state.clear()
    state[report.when] = report
    if report.outcome == "rerun":
        state["rerun"] = True
    if report.when != "teardown":
        return
    state = _REPORTS.pop(report.nodeid, state)
    if state.get("rerun"):
        return
    final = _final_report(state)
    if final is not None:
        _append_record(final)


def _final_report(state: dict[str, Any]) -> Any | None:
    teardown = state.get("teardown")
    if teardown is not None and teardown.outcome == "failed":
        return teardown
    call = state.get("call")
    if call is not None:
        return call
    setup = state.get("setup")
    if setup is not None and setup.outcome in {"failed", "skipped"}:
        return setup
    return None


def _append_record(report: Any) -> None:
    assert _JOURNAL_PATH is not None
    location = list(report.location) if report.location is not None else []
    record = {
        "nodeid": report.nodeid,
        "location": location,
        "phase": report.when,
        "outcome": report.outcome,
        "duration": report.duration,
        "message": getattr(report, "longreprtext", ""),
        "wasxfail": getattr(report, "wasxfail", None),
    }
    payload = (json.dumps(record, ensure_ascii=True) + "\n").encode()
    descriptor = os.open(_JOURNAL_PATH, os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o600)
    try:
        view = memoryview(payload)
        while view:
            written = os.write(descriptor, view)
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
