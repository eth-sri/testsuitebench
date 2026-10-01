from __future__ import annotations

import json
from pathlib import Path

import pytest

from programbench.iteration_inputs import directory_digest, snapshot_iteration_inputs


def _write_task(root: Path, task: str, name: str, contents: str) -> None:
    task_dir = root / task
    task_dir.mkdir(parents=True, exist_ok=True)
    (task_dir / name).write_text(contents)


def test_snapshot_iteration_inputs_copies_and_hashes_each_named_input(
    tmp_path: Path,
) -> None:
    task = "owner__repo.rev"
    spec = tmp_path / "iter_0" / "spec"
    tests = tmp_path / "iter_0" / "test"
    stage = tmp_path / "iter_1" / "stages" / "candidate-evaluation"
    _write_task(spec, task, "spec.md", "spec v0\n")
    _write_task(tests, task, "tests.tar.gz", "tests v0\n")

    manifest_path = snapshot_iteration_inputs(
        stage_dir=stage,
        task=task,
        sources={"spec": spec, "test": tests},
    )

    manifest = json.loads(manifest_path.read_text())
    assert (stage / "spec" / task / "spec.md").read_text() == "spec v0\n"
    assert (stage / "test" / task / "tests.tar.gz").read_text() == "tests v0\n"
    assert manifest["inputs"]["spec"]["source"] == str(spec)
    assert manifest["inputs"]["spec"]["snapshot"] == str(stage / "spec")
    assert manifest["inputs"]["spec"]["sha256"] == directory_digest(spec / task)


def test_snapshot_is_reused_only_while_sources_are_unchanged(tmp_path: Path) -> None:
    task = "owner__repo.rev"
    spec = tmp_path / "iter_0" / "spec"
    stage = tmp_path / "iter_1" / "stages" / "generated-test-generation"
    _write_task(spec, task, "spec.md", "before\n")

    first = snapshot_iteration_inputs(
        stage_dir=stage, task=task, sources={"spec": spec}
    )
    second = snapshot_iteration_inputs(
        stage_dir=stage, task=task, sources={"spec": spec}
    )
    assert first == second

    (spec / task / "spec.md").write_text("after\n")
    with pytest.raises(FileExistsError, match="inputs changed"):
        snapshot_iteration_inputs(
            stage_dir=stage, task=task, sources={"spec": spec}
        )

    snapshot_iteration_inputs(
        stage_dir=stage,
        task=task,
        sources={"spec": spec},
        force=True,
    )
    assert (stage / "spec" / task / "spec.md").read_text() == "after\n"


def test_snapshot_requires_the_requested_task_in_every_input(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="Iteration input is missing"):
        snapshot_iteration_inputs(
            stage_dir=tmp_path / "stage",
            task="missing",
            sources={"spec": tmp_path / "spec"},
        )
