import os
from pathlib import Path

import pytest

from programbench.utils import reference_test_store
from programbench.utils.reference_test_store import resolve_reference_tests_dir
from scripts.dataset import fetch_task_inputs
from scripts.dataset.upload_reference_tests_to_hf import archive_reference_tests, select_instances

TASK = "org__tool.abc123"


def _reference_tests(root: Path) -> Path:
    branch = root / TASK / "branch_a"
    (branch / "eval").mkdir(parents=True)
    (branch / "eval" / "run.sh").write_text("#!/bin/sh\n")
    (branch / "eval" / "run.sh").chmod(0o755)
    # Fixtures that the "data" extraction filter would refuse.
    (branch / "abs_link").symlink_to("/media/")
    (branch / "dangling").symlink_to("/nonexistent")
    return root


@pytest.fixture
def fake_hub(tmp_path, monkeypatch):
    snapshot = tmp_path / "snapshot"
    archive_reference_tests(_reference_tests(tmp_path / "source") / TASK, snapshot / "tests" / f"{TASK}.tar.gz")
    calls = []

    def snapshot_download(repo_id, *, repo_type, revision, allow_patterns):
        calls.append((repo_id, revision, allow_patterns))
        return str(snapshot)

    monkeypatch.setattr("huggingface_hub.snapshot_download", snapshot_download)
    monkeypatch.setattr(reference_test_store, "REFERENCE_TESTS_CACHE", tmp_path / "cache")
    reference_test_store._download_reference_tests.cache_clear()
    yield calls
    reference_test_store._download_reference_tests.cache_clear()


def test_local_reference_tests_dir_is_returned_unchanged(tmp_path):
    assert resolve_reference_tests_dir(tmp_path, TASK) == tmp_path
    assert resolve_reference_tests_dir("extracted-tests", TASK) == Path("extracted-tests")


def test_hf_reference_tests_are_downloaded_per_instance_and_keep_fixture_symlinks(fake_hub, tmp_path):
    root = resolve_reference_tests_dir("hf://someone/pb-test@v1", TASK)

    branch = root / TASK / "branch_a"
    assert root.parent == tmp_path / "cache"
    assert fake_hub == [("someone/pb-test", "v1", f"tests/{TASK}.tar.gz")]
    assert os.readlink(branch / "abs_link") == "/media/"
    assert os.readlink(branch / "dangling") == "/nonexistent"
    assert os.access(branch / "eval" / "run.sh", os.X_OK)
    assert resolve_reference_tests_dir("hf://someone/pb-test@v1", TASK) == root
    assert len(fake_hub) == 1


def test_fetch_extracts_missing_reference_tests_and_keeps_present_ones(fake_hub, tmp_path):
    fetch_task_inputs.fetch_reference_tests(TASK, "hf://someone/pb-test", tmp_path / "extracted-tests")
    assert (tmp_path / "extracted-tests" / TASK / "branch_a" / "eval" / "run.sh").is_file()

    fetch_task_inputs.fetch_reference_tests(TASK, "hf://someone/pb-test", tmp_path / "extracted-tests")
    assert len(fake_hub) == 1


def test_upload_selects_listed_instances_and_rejects_missing_ones(tmp_path):
    source = _reference_tests(tmp_path / "extracted-tests")
    (source / "org__other.def456").mkdir()
    tasks = tmp_path / "tasks.txt"
    tasks.write_text(f"# benchmark\n{TASK}\n")

    assert select_instances(source, tasks, None) == [TASK]
    assert select_instances(source, None, None) == ["org__other.def456", TASK]
    tasks.write_text("org__missing.000000\n")
    with pytest.raises(SystemExit, match="org__missing"):
        select_instances(source, tasks, None)
