from pathlib import Path

from programbench.iteration_inputs import snapshot_iteration_inputs
from programbench.iteration_polish import _copy_tree


def test_stage_and_next_iteration_copies_share_unchanged_files(tmp_path: Path) -> None:
    task = "org__repo.rev"
    source_root = tmp_path / "iter_0" / "mutant"
    source = source_root / task / "repo_1" / "source.c"
    source.parent.mkdir(parents=True)
    source.write_text("int main(void) { return 1; }\n")

    stage = tmp_path / "iter_1" / "stages" / "mutant-eval"
    snapshot_iteration_inputs(
        stage_dir=stage,
        task=task,
        sources={"mutant": source_root},
    )
    next_task = tmp_path / "iter_1" / "mutant" / task
    _copy_tree(source_root / task, next_task, force=False, label="mutant")

    staged = stage / "mutant" / task / "repo_1" / "source.c"
    copied = next_task / "repo_1" / "source.c"
    assert source.stat().st_ino == staged.stat().st_ino == copied.stat().st_ino
