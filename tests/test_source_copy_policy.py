from pathlib import Path

from programbench.constants import SOURCE_COPY_EXCLUDES
from programbench.mutants import _repo_copy_ignore
from programbench.reference_test_preparation import _stage_build_source


def test_ground_truth_and_mutant_staging_share_source_excludes(tmp_path: Path) -> None:
    branch = tmp_path / "branch"
    target = tmp_path / "target"
    branch.mkdir()
    for name in (*SOURCE_COPY_EXCLUDES, "kept.txt"):
        (branch / name).write_text(name)

    _stage_build_source(branch, target)

    assert sorted(path.name for path in target.iterdir()) == ["kept.txt"]
    names = [*SOURCE_COPY_EXCLUDES, "kept.txt"]
    assert set(_repo_copy_ignore("", names)) == set(SOURCE_COPY_EXCLUDES)
    assert ".gitignore" in SOURCE_COPY_EXCLUDES
