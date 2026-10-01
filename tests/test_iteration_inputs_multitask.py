import json
from pathlib import Path

from programbench.iteration_inputs import snapshot_iteration_inputs


def _write_task(root: Path, task: str, contents: str) -> None:
    task_dir = root / task
    task_dir.mkdir(parents=True)
    (task_dir / "input.txt").write_text(contents)


def test_multiple_tasks_share_a_stage_without_replacing_each_other(tmp_path: Path) -> None:
    source = tmp_path / "iter_0" / "spec"
    stage = tmp_path / "iter_1" / "stages" / "candidate-evaluation"
    first_task = "owner__first.rev"
    second_task = "owner__second.rev"
    _write_task(source, first_task, "first\n")
    _write_task(source, second_task, "second\n")

    first_manifest = snapshot_iteration_inputs(
        stage_dir=stage,
        task=first_task,
        sources={"spec": source},
    )
    second_manifest = snapshot_iteration_inputs(
        stage_dir=stage,
        task=second_task,
        sources={"spec": source},
    )

    assert first_manifest == stage / "manifests" / f"{first_task}.json"
    assert second_manifest == stage / "manifests" / f"{second_task}.json"
    assert json.loads(first_manifest.read_text())["task"] == first_task
    assert json.loads(second_manifest.read_text())["task"] == second_task
    assert (stage / "spec" / first_task / "input.txt").read_text() == "first\n"
    assert (stage / "spec" / second_task / "input.txt").read_text() == "second\n"
