from __future__ import annotations

import json
from pathlib import Path

import pytest

from programbench.test_spec_links import (
    load_reference_test_functions,
    normalize_link_manifest,
    numbered_spec_sections,
)


def _write_inputs(tmp_path: Path, task: str = "owner__repo.rev") -> tuple[Path, Path]:
    spec_root = tmp_path / "spec"
    tests_root = tmp_path / "reference-tests"
    (spec_root / task).mkdir(parents=True)
    (spec_root / task / "spec.md").write_text("# Task\n\n## Spec 1\nAlpha.\n\n## Spec 2\nBeta.\n")
    (tests_root / task / "branch-a").mkdir(parents=True)
    (tests_root / task / "branch-a" / "test_cli.py").write_text(
        "def test_alpha(value):\n    assert value == 'alpha'\n"
    )
    (tests_root / task / "tests.json").write_text(
        json.dumps(
            {
                "branches": {
                    "branch-a": {
                        "ignored": False,
                        "tests": [
                            "tests.test_cli.test_alpha[one]",
                            "tests.test_cli.test_alpha[two]",
                        ],
                    },
                    "ignored-branch": {
                        "ignored": True,
                        "tests": ["tests.test_ignored"],
                    },
                }
            }
        )
    )
    return spec_root, tests_root


def test_reference_manifest_collapses_parameter_cases_to_functions(
    tmp_path: Path,
) -> None:
    _, tests_root = _write_inputs(tmp_path)

    functions = load_reference_test_functions(tests_root / "owner__repo.rev")

    assert functions == [
        {
            "id": "branch-a/tests.test_cli.test_alpha",
            "branch": "branch-a",
            "name": "tests.test_cli.test_alpha",
            "target_specs": [],
            "description": "",
            "cases": [
                "tests.test_cli.test_alpha[one]",
                "tests.test_cli.test_alpha[two]",
            ],
        }
    ]


def test_normalize_links_rejects_unknown_or_missing_spec_targets(
    tmp_path: Path,
) -> None:
    spec_root, tests_root = _write_inputs(tmp_path)
    functions = load_reference_test_functions(tests_root / "owner__repo.rev")
    valid_specs = numbered_spec_sections(spec_root / "owner__repo.rev")

    with pytest.raises(ValueError, match="Unknown target_spec"):
        normalize_link_manifest(
            {"test_functions": [{"id": functions[0]["id"], "target_specs": ["Spec 3"]}]},
            task="owner__repo.rev",
            functions=functions,
            valid_specs=valid_specs,
        )

    with pytest.raises(ValueError, match="Missing target_specs"):
        normalize_link_manifest(
            {"test_functions": []},
            task="owner__repo.rev",
            functions=functions,
            valid_specs=valid_specs,
        )

