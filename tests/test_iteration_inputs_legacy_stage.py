import json
from pathlib import Path

from programbench.iteration_inputs import snapshot_iteration_inputs


def test_task_scoped_manifest_migrates_past_a_legacy_global_manifest(
    tmp_path: Path,
) -> None:
    task = "ast-grep__ast-grep.rev"
    source = tmp_path / "iter_0" / "spec"
    source_task = source / task
    source_task.mkdir(parents=True)
    (source_task / "spec.md").write_text("new task\n")

    stage = tmp_path / "iter_1" / "stages" / "candidate-evaluation"
    stage.mkdir(parents=True)
    (stage / "inputs.json").write_text(
        json.dumps({"schema_version": 1, "task": "old__task.rev", "inputs": {}})
    )

    manifest = snapshot_iteration_inputs(
        stage_dir=stage,
        task=task,
        sources={"spec": source},
    )

    assert manifest == stage / "manifests" / f"{task}.json"
    assert (stage / "inputs.json").is_file()
    assert (stage / "spec" / task / "spec.md").read_text() == "new task\n"
