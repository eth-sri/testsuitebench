import json
from pathlib import Path

from programbench.mutant_storage import seal_mutant_sources, source_blob_name
from scripts.dataset.upload_mutant_store_to_hf import _instance_upload, _iter_selected


def _write(root: Path, files: dict[str, str]) -> Path:
    for name, content in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    return root


def _fixture(tmp_path: Path) -> tuple[Path, Path]:
    ground_truth = _write(tmp_path / "gt" / "org__tool.abc123", {"tool.c": "original", "shared.h": "gt header"})
    instance = tmp_path / "mutants" / "org__tool.abc123"
    (instance / ".artifacts" / "sha256").mkdir(parents=True)
    (instance / ".artifacts" / "sha256" / "deadbeef.gz").write_bytes(b"\x1f\x8b")
    (instance / "mutants.json").write_text("{}")
    for name, mutation in [("repo_1", "mutant A"), ("repo_2", "mutant A"), ("repo_10", "mutant B")]:
        _write(instance / name, {"tool.c": mutation, "shared.h": "generated"})
    return instance, tmp_path / "gt"


def test_unsealed_suite_is_sealed_into_staging_without_being_modified(tmp_path: Path) -> None:
    instance, ground_truth = _fixture(tmp_path)

    upload = _instance_upload(instance, ground_truth, tmp_path / "staging")
    names = [name for name, _ in upload.upload_files]

    # 3 repos, 6 differing files, 3 unique contents -> sources.json + 3 blobs.
    assert names[:2] == ["mutants.json", ".artifacts/sha256/deadbeef.gz"]
    assert sorted(names[2:])[0] == source_blob_name(
        sorted(
            json.loads((tmp_path / "staging" / instance.name / "sources.json").read_text())["overlays"][
                "repo_1"
            ].values()
        )[0]
    )
    assert len(names) == 6
    # The source directory keeps its repo_N trees; only the staging copy is sealed.
    assert sorted(p.name for p in instance.glob("repo_*")) == ["repo_1", "repo_10", "repo_2"]


def test_sealed_suite_uploads_in_place(tmp_path: Path) -> None:
    instance, ground_truth = _fixture(tmp_path)
    seal_mutant_sources(instance, ground_truth / instance.name)

    upload = _instance_upload(instance, ground_truth, tmp_path / "staging")
    names = [name for name, _ in upload.upload_files]

    assert "sources.json" in names
    assert sum(name.startswith(".artifacts/sources/") for name in names) == 3
    assert all(path.is_relative_to(instance) for _, path in upload.upload_files)
    assert not (tmp_path / "staging").exists()


def test_instance_upload_without_ground_truth_keeps_only_eval_inputs(tmp_path: Path) -> None:
    instance, _ = _fixture(tmp_path)

    upload = _instance_upload(instance, None, tmp_path / "staging")

    assert upload.source_files == []
    assert [name for name, _ in upload.upload_files] == ["mutants.json", ".artifacts/sha256/deadbeef.gz"]


def test_iter_selected_skips_directories_without_a_manifest(tmp_path: Path) -> None:
    instance, _ = _fixture(tmp_path)
    (instance.parent / "org__other.def456").mkdir()

    assert [u.instance_id for u in _iter_selected(instance.parent, None, None, tmp_path / "staging", 1)] == [
        "org__tool.abc123"
    ]
