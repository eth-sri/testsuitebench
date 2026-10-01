# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the root directory of
# this source tree.

"""Run-scoped list of mutants that must not participate in mutation score."""

from __future__ import annotations

import json
from pathlib import Path

from programbench.skipped_tests import skipped_tests_path


def load_skipped_mutants(root_or_file: str | Path | None, *, task: str) -> set[str]:
    """Read ``<root>/<task>.json`` (or a direct JSON path) and return the mutant ids to drop."""
    if not root_or_file:
        return set()
    path = skipped_tests_path(root_or_file, task)
    document = json.loads(path.read_text())
    if document["instance_id"] != task:
        raise ValueError(f"Skipped-mutant list is for {document['instance_id']}, not {task}: {path}")
    return {item["id"] for item in document["skipped_mutants"]}
