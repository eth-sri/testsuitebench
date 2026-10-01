"""Injected pytest plugin: do not execute tests already excluded from scoring."""
from __future__ import annotations

import json
import os
from pathlib import Path
import re


def function_name(name: str) -> str:
    return re.split(r"\[| \(", name, maxsplit=1)[0].partition("@")[0]


def pytest_collection_modifyitems(config, items):
    path = os.environ.get("PROGRAMBENCH_PYTEST_EXCLUSIONS")
    if not path:
        return
    excluded = set(json.loads(Path(path).read_text()))
    kept, removed = [], []
    for item in items:
        # pytest's JUnit classname is built from the collection nodeid, with
        # paths converted to modules and the .py extension stripped.
        nodeid = function_name(item.nodeid)
        parts = nodeid.split("::")
        module = parts[0].replace("/", ".").removesuffix(".py")
        names = {".".join([module, *parts[1:]])}
        # Some runners collect from /workspace rather than /workspace/eval.
        if module.startswith("eval."):
            names.add(".".join([module[5:], *parts[1:]]))
        else:
            names.add(".".join(["eval." + module, *parts[1:]]))
        (removed if names & excluded else kept).append(item)
    if removed:
        items[:] = kept
        config.hook.pytest_deselected(items=removed)
