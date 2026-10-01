# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

"""Manifest helpers for links between fixed tests and specification sections."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from programbench.constants import TASKS_DIR


TEST_SPEC_LINKS_FILENAME = "test_spec_links.json"


def _test_function_name(name: str) -> str:
    """Collapse parametrized test cases to the test function recorded in source."""
    return re.split(r"\[| \(", name, maxsplit=1)[0].partition("@")[0]


def load_reference_test_functions(
    task_tests: Path, *, skipped_tests: set[str] | None = None,
) -> list[dict[str, Any]]:
    manifest_path = task_tests / "tests.json"
    if not manifest_path.is_file():
        manifest_path = TASKS_DIR / task_tests.name / "tests.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Reference-test manifest does not exist: {manifest_path}")
    manifest = json.loads(manifest_path.read_text())
    excluded = {_test_function_name(name) for name in (skipped_tests or ())}
    excluded.update(
        f"{branch}/{_test_function_name(str(item['name']))}"
        for branch, info in (manifest.get("branches") or {}).items()
        for item in info.get("ignored_tests") or []
    )
    functions: dict[tuple[str, str], dict[str, Any]] = {}
    for branch, branch_info in sorted((manifest.get("branches") or {}).items()):
        if branch_info.get("ignored"):
            continue
        for raw_name in branch_info.get("tests") or []:
            name = _test_function_name(str(raw_name))
            if f"{branch}/{name}" in excluded:
                continue
            key = (str(branch), name)
            entry = functions.setdefault(
                key,
                {
                    "id": f"{branch}/{name}",
                    "branch": str(branch),
                    "name": name,
                    "target_specs": [],
                    "description": "",
                },
            )
            case_name = str(raw_name)
            if case_name != name:
                entry.setdefault("cases", []).append(case_name)
    return list(functions.values())


def numbered_spec_sections(task_spec: Path) -> list[str]:
    sections: set[int] = set()
    for path in sorted(task_spec.rglob("*")):
        if not path.is_file():
            continue
        try:
            text = path.read_text(errors="strict")
        except (OSError, UnicodeError):
            continue
        sections.update(
            int(number)
            for number in re.findall(r"(?im)^##\s+Spec\s+(\d+)\b", text)
        )
    if not sections:
        raise RuntimeError(f"No numbered '## Spec N' sections found under {task_spec}")
    return [f"Spec {number}" for number in sorted(sections)]


def starter_manifest(*, task: str, functions: list[dict[str, Any]]) -> dict[str, Any]:
    return {"instance_id": task, "test_functions": functions}


def normalize_link_manifest(
    data: object,
    *,
    task: str,
    functions: list[dict[str, Any]],
    valid_specs: list[str],
    require_complete: bool = True,
) -> dict[str, Any]:
    raw_functions = data.get("test_functions", []) if isinstance(data, dict) else []
    raw_by_id = {
        str(item.get("id", "")): item
        for item in raw_functions
        if isinstance(item, dict) and item.get("id")
    }
    valid_spec_set = set(valid_specs)
    normalized = []
    incomplete = []
    for function in functions:
        raw = raw_by_id.get(function["id"], {})
        targets = []
        for value in raw.get("target_specs", []) if isinstance(raw, dict) else []:
            match = re.search(r"\bSpec\s+(\d+)\b", str(value), flags=re.IGNORECASE)
            target = f"Spec {int(match.group(1))}" if match else str(value).strip()
            if target not in valid_spec_set:
                raise ValueError(
                    f"Unknown target_spec {value!r} for {function['id']}; "
                    f"expected one of {valid_specs}"
                )
            if target not in targets:
                targets.append(target)
        if not targets:
            incomplete.append(function["id"])
        entry = {**function, "target_specs": targets}
        entry["description"] = (
            str(raw.get("description", "")).strip()
            if isinstance(raw, dict)
            else ""
        )
        normalized.append(entry)
    if require_complete and incomplete:
        preview = ", ".join(incomplete[:5])
        suffix = "" if len(incomplete) <= 5 else f" (and {len(incomplete) - 5} more)"
        raise ValueError(f"Missing target_specs for {preview}{suffix}")
    return {
        "instance_id": task,
        "spec_sections": valid_specs,
        "test_functions": normalized,
    }
