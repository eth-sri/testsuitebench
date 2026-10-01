from __future__ import annotations

import tarfile

import pytest

from programbench.constants import GROUND_TRUTH_LIB_DIR
from programbench.utils.ground_truth_store import resolve_ground_truth_dir, write_ground_truth_submission_archive


def test_resolve_ground_truth_dir_returns_local_path_unchanged(tmp_path):
    local = tmp_path / "ground_truth" / "executable"
    assert resolve_ground_truth_dir(str(local), "org__repo.123") == local


def test_resolve_ground_truth_dir_downloads_from_huggingface(monkeypatch, tmp_path):
    calls = []

    def fake_snapshot_download(repo_id, *, repo_type, revision, allow_patterns):
        calls.append((repo_id, repo_type, revision, allow_patterns))
        return str(tmp_path)

    monkeypatch.setattr("huggingface_hub.snapshot_download", fake_snapshot_download)

    result = resolve_ground_truth_dir("hf://org/pb-ground-truth@v2", "org__repo.123")

    assert result == tmp_path / "executable"
    assert calls == [("org/pb-ground-truth", "dataset", "v2", "executable/org__repo.123/**")]


def test_write_ground_truth_submission_archive_packages_executable_and_compile_script(tmp_path):
    executable = tmp_path / "executable"
    executable.write_bytes(b"binary-contents")
    output = tmp_path / "submission.tar.gz"

    write_ground_truth_submission_archive(executable, output)

    with tarfile.open(output, "r:gz") as archive:
        names = sorted(archive.getnames())
        assert names == ["compile.sh", "executable"]
        assert archive.extractfile("executable").read() == b"binary-contents"


def test_write_ground_truth_submission_archive_bundles_sibling_lib_dir(tmp_path):
    executable = tmp_path / "executable"
    executable.write_bytes(b"binary-contents")
    (tmp_path / "lib").mkdir()
    (tmp_path / "lib" / "libfoo.so.1").write_bytes(b"lib-contents")
    output = tmp_path / "submission.tar.gz"

    write_ground_truth_submission_archive(executable, output)

    with tarfile.open(output, "r:gz") as archive:
        names = sorted(archive.getnames())
        assert names == ["compile.sh", "executable", "lib", "lib/libfoo.so.1"]
        assert archive.extractfile("lib/libfoo.so.1").read() == b"lib-contents"


def test_write_ground_truth_submission_archive_compile_script_installs_lib_at_fixed_path(tmp_path):
    """compile.sh must install ./lib at GROUND_TRUTH_LIB_DIR, not rely on the
    ./lib sibling surviving: evaluation wipes WORKSPACE_DIR before every test
    branch and only round-trips the bare executable file across that wipe."""
    executable = tmp_path / "executable"
    executable.write_bytes(b"binary-contents")
    (tmp_path / "lib").mkdir()
    (tmp_path / "lib" / "libfoo.so.1").write_bytes(b"lib-contents")
    output = tmp_path / "submission.tar.gz"

    write_ground_truth_submission_archive(executable, output)

    with tarfile.open(output, "r:gz") as archive:
        compile_sh = archive.extractfile("compile.sh").read().decode()
    assert f"mkdir -p {GROUND_TRUTH_LIB_DIR}" in compile_sh
    assert f"cp -f ./lib/* {GROUND_TRUTH_LIB_DIR}/" in compile_sh


def test_write_ground_truth_submission_archive_compile_script_skips_lib_install_when_absent(tmp_path):
    executable = tmp_path / "executable"
    executable.write_bytes(b"binary-contents")
    output = tmp_path / "submission.tar.gz"

    write_ground_truth_submission_archive(executable, output)

    with tarfile.open(output, "r:gz") as archive:
        compile_sh = archive.extractfile("compile.sh").read().decode()
    assert GROUND_TRUTH_LIB_DIR not in compile_sh


def test_write_ground_truth_submission_archive_omits_empty_lib_dir(tmp_path):
    executable = tmp_path / "executable"
    executable.write_bytes(b"binary-contents")
    (tmp_path / "lib").mkdir()
    output = tmp_path / "submission.tar.gz"

    write_ground_truth_submission_archive(executable, output)

    with tarfile.open(output, "r:gz") as archive:
        assert sorted(archive.getnames()) == ["compile.sh", "executable"]


def test_write_ground_truth_submission_archive_raises_when_executable_missing(tmp_path):
    with pytest.raises(FileNotFoundError):
        write_ground_truth_submission_archive(tmp_path / "missing", tmp_path / "submission.tar.gz")
