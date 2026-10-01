# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the root directory of
# this source tree.

"""Run-scoped list of reference tests that must not participate in scoring."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from programbench.constants import TASKS_DIR


def skipped_tests_path(root_or_file: str | Path, task: str) -> Path:
    """Resolve either a direct JSON path or a ``<root>/<task>.json`` root."""
    path = Path(root_or_file)
    if path.suffix == ".json":
        return path
    return path / f"{task}.json"


def test_function_name(name: str) -> str:
    return re.split(r"\[| \(", name, maxsplit=1)[0].partition("@")[0]


def normalize_test_function_names(names: set[str]) -> set[str]:
    return {test_function_name(name) for name in names}


def _canonical_entries(task: str, *, tasks_dir: Path = TASKS_DIR) -> list[dict[str, Any]]:
    metadata_path = tasks_dir / task / "tests.json"
    if not metadata_path.is_file():
        raise FileNotFoundError(f"Test metadata does not exist for {task}: {metadata_path}")
    metadata = json.loads(metadata_path.read_text())
    entries = []
    for branch, info in (metadata.get("branches") or {}).items():
        if info.get("ignored"):
            entries.extend(
                {
                    "name": f"{branch}/{test_function_name(str(name))}",
                    "reasons": [{"id": "ignored_branch"}],
                }
                for name in info.get("tests") or []
            )
        for item in info.get("ignored_tests") or []:
            entries.append({
                "name": f"{branch}/{test_function_name(str(item['name']))}",
                "reasons": list(item.get("reasons") or []),
            })
    return entries


def _normalize_entries(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_name: dict[str, dict[str, Any]] = {}
    for raw in entries:
        name = str(raw.get("name", "")).strip()
        branch, separator, test_name = name.partition("/")
        if not separator or not branch or not test_name:
            raise ValueError(f"Invalid skipped-test name (expected branch/test): {name!r}")
        reasons = [dict(reason) for reason in raw.get("reasons") or [] if isinstance(reason, dict)]
        existing = by_name.setdefault(name, {"name": name, "reasons": []})
        seen = {json.dumps(reason, sort_keys=True) for reason in existing["reasons"]}
        for reason in reasons:
            key = json.dumps(reason, sort_keys=True)
            if key not in seen:
                existing["reasons"].append(reason)
                seen.add(key)
    return [by_name[name] for name in sorted(by_name)]


def initialize_skipped_tests(
    *, task: str, output: str | Path, tasks_dir: Path = TASKS_DIR, force: bool = False,
) -> dict[str, Any]:
    """Create the run list from the canonical ``ignored_tests`` registry."""
    path = skipped_tests_path(output, task)
    if path.exists() and not force:
        return load_skipped_tests_document(path, task=task)
    document = {
        "instance_id": task,
        "skipped_tests": _normalize_entries(_canonical_entries(task, tasks_dir=tasks_dir)),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n")
    return document


def load_skipped_tests_document(root_or_file: str | Path, *, task: str) -> dict[str, Any]:
    path = skipped_tests_path(root_or_file, task)
    if not path.is_file():
        raise FileNotFoundError(f"Skipped-test list does not exist for {task}: {path}")
    document = json.loads(path.read_text())
    instance_id = str(document.get("instance_id", ""))
    if instance_id and instance_id != task:
        raise ValueError(f"Skipped-test list is for {instance_id}, not {task}: {path}")
    return {"instance_id": task, "skipped_tests": _normalize_entries(document.get("skipped_tests") or [])}


def load_skipped_tests(root_or_file: str | Path | None, *, task: str) -> set[str]:
    if not root_or_file:
        return set()
    document = load_skipped_tests_document(root_or_file, task=task)
    return {item["name"] for item in document["skipped_tests"]}


def add_skipped_tests(
    root_or_file: str | Path,
    *,
    task: str,
    names: set[str],
    reason: str = "our_gt_gold_fail",
) -> list[str]:
    """Add names idempotently and return the newly added names.

    Reasons written here carry the ``our_gt_`` prefix so entries our pipeline
    discovered stay distinguishable from the canonical ``tests.json`` ones.
    """
    path = skipped_tests_path(root_or_file, task)
    document = load_skipped_tests_document(path, task=task)
    names = normalize_test_function_names(names)
    existing = {item["name"] for item in document["skipped_tests"]}
    added = sorted(names - existing)
    entries = list(document["skipped_tests"])
    entries.extend({"name": name, "reasons": [{"id": reason}]} for name in added)
    document["skipped_tests"] = _normalize_entries(entries)
    path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n")
    return added
