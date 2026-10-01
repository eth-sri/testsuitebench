"""Sealing repo_N trees down to the information needed to rebuild them."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from programbench.mutant_storage import (
    SOURCE_ARTIFACT_DIR,
    SOURCES_MANIFEST,
    ground_truth_digest,
    materialize_mutant_sources,
    seal_mutant_sources,
    seal_mutant_store,
    store_digest,
    tracked_sources,
)
from programbench.utils.ground_truth_store import resolve_implementation_dir


def _write(root: Path, files: dict[str, str]) -> Path:
    for name, content in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    return root


@pytest.fixture
def suite(tmp_path: Path) -> tuple[Path, Path]:
    """A three-mutant suite whose overlay is shared only partially."""
    ground_truth = _write(
        tmp_path / "gt" / "org__tool.abc123",
        {"tool.c": "original", "shared.h": "gt header", "dropped.c": "gone", "doc/readme.md": "docs"},
    )
    instance = tmp_path / "mutants" / "org__tool.abc123"
    # repo_1 and repo_2 carry the same mutation; repo_10 differs. shared.h is
    # regenerated identically everywhere. dropped.c is deleted everywhere.
    for name, mutation in [("repo_1", "mutant A"), ("repo_2", "mutant A"), ("repo_10", "mutant B")]:
        _write(instance / name, {"tool.c": mutation, "shared.h": "generated", "doc/readme.md": "docs"})
    _write(instance / "repo_1" / "build", {"CMakeCache.txt": "host paths"})
    (instance / "repo_1" / "tool.o").write_bytes(b"\x7fELF object")
    (instance / "repo_1" / "tool").write_bytes(b"\x7fELF linked binary")
    return instance, ground_truth


def test_seal_stores_each_unique_content_once_and_drops_build_output(suite) -> None:
    instance, ground_truth = suite

    status = seal_mutant_sources(instance, ground_truth)
    manifest = json.loads((instance / SOURCES_MANIFEST).read_text())

    # 6 differing files across 3 repos collapse to 3 blobs: "mutant A",
    # "mutant B" and "generated". doc/readme.md matches the ground truth.
    assert status == {"repos": 3, "blobs": 3, "overlay_entries": 6}
    assert manifest["overlays"]["repo_1"] == manifest["overlays"]["repo_2"]
    assert manifest["overlays"]["repo_1"]["tool.c"] != manifest["overlays"]["repo_10"]["tool.c"]
    assert sorted(manifest["overlays"]["repo_10"]) == ["shared.h", "tool.c"]
    assert manifest["removed"] == ["dropped.c"]
    assert manifest["ground_truth"] == ground_truth.as_posix()
    assert not list(instance.glob("repo_*"))


def test_materialize_rebuilds_every_repo_without_touching_the_ground_truth(suite) -> None:
    instance, ground_truth = suite
    before = {repo.name: {k: d for k, (_, d) in tracked_sources(repo).items()} for repo in instance.glob("repo_*")}
    ground_truth_before = {k: d for k, (_, d) in tracked_sources(ground_truth).items()}

    seal_mutant_sources(instance, ground_truth)

    for repo, expected in before.items():
        with materialize_mutant_sources(instance, repo) as rebuilt:
            assert {k: d for k, (_, d) in tracked_sources(rebuilt).items()} == expected
            assert not (rebuilt / "dropped.c").exists()
    # Rebuilt trees are hardlinked from the ground truth, so an overlay write that
    # did not replace the link first would silently corrupt the shared original.
    assert {k: d for k, (_, d) in tracked_sources(ground_truth).items()} == ground_truth_before


def test_materialize_prefers_an_unsealed_repo_tree(suite) -> None:
    instance, _ = suite

    with materialize_mutant_sources(instance, "repo_1") as repo:
        assert repo == instance / "repo_1"
        assert (repo / "tool.c").read_text() == "mutant A"


def test_seal_store_compacts_executables_and_stamps_a_digest(suite) -> None:
    instance, ground_truth = suite
    (instance / "repo_1" / "executable").write_bytes(b"\x7fELF mutant one")
    (instance / "repo_2" / "executable").write_bytes(b"\x7fELF mutant one")
    (instance / "mutants.json").write_text(
        json.dumps({"mutants": [{"id": "repo_1", "payload": "repo_1/executable"},
                                {"id": "repo_2", "payload": "repo_2/executable"}]})
    )

    status = seal_mutant_store(instance, ground_truth)
    manifest = json.loads((instance / "mutants.json").read_text())

    # Both mutants compiled to identical bytes, so they share one artifact.
    assert status["compacted"] == 2
    assert status["artifacts"] == 1
    assert manifest["mutants"][0]["artifact"]["sha256"] == manifest["mutants"][1]["artifact"]["sha256"]
    assert len((instance / "digest").read_text().strip()) == 64


def test_materialize_rebuilds_from_a_relocated_ground_truth_but_rejects_a_substituted_one(suite, tmp_path) -> None:
    instance, ground_truth = suite
    seal_mutant_sources(instance, ground_truth)
    relocated = shutil.copytree(ground_truth, tmp_path / "elsewhere" / ground_truth.name)
    shutil.rmtree(ground_truth)

    # The recorded path is gone, so only the override can rebuild the overlay.
    with pytest.raises(FileNotFoundError):
        with materialize_mutant_sources(instance, "repo_1"):
            pass
    with materialize_mutant_sources(instance, "repo_1", relocated) as repo:
        assert (repo / "tool.c").read_text() == "mutant A"
        assert (repo / "shared.h").read_text() == "generated"

    (relocated / "shared.h").write_text("a different upstream release")
    ground_truth_digest.cache_clear()
    with pytest.raises(ValueError, match="does not match the one"):
        with materialize_mutant_sources(instance, "repo_1", relocated):
            pass


def test_base_digest_ignores_what_never_reaches_a_rebuilt_repo(suite, tmp_path) -> None:
    instance, ground_truth = suite
    seal_mutant_sources(instance, ground_truth)
    manifest_path = instance / SOURCES_MANIFEST
    manifest = json.loads(manifest_path.read_text())
    removed = frozenset(manifest["removed"])

    # Build output is untracked, and dropped.c is deleted from every rebuild, so
    # a base tree missing it (as a HuggingFace archive is) is still the right one.
    (ground_truth / "tool.o").write_bytes(b"\x7fELF object")
    (ground_truth / "dropped.c").unlink()
    ground_truth_digest.cache_clear()
    assert ground_truth_digest(ground_truth, removed) == manifest["base_digest"]
    with materialize_mutant_sources(instance, "repo_1") as repo:
        assert (repo / "tool.c").read_text() == "mutant A"

    del manifest["base_digest"]
    manifest_path.write_text(json.dumps(manifest))
    (ground_truth / "shared.h").write_text("unverifiable drift")
    with materialize_mutant_sources(instance, "repo_1") as repo:
        assert (repo / "shared.h").read_text() == "generated"


def test_blobs_shard_by_digest_prefix_and_a_flat_store_still_reads(suite) -> None:
    instance, ground_truth = suite
    seal_mutant_sources(instance, ground_truth)
    blobs = sorted((instance / SOURCE_ARTIFACT_DIR).rglob("*.gz"))
    sharded = store_digest(instance)

    # The Hub caps a directory at 10k files, which universal-ctags' 10212 blobs break.
    assert [blob.parent.name for blob in blobs] == [blob.name[:2] for blob in blobs]

    for blob in blobs:
        blob.replace(instance / SOURCE_ARTIFACT_DIR / blob.name)
        blob.parent.rmdir()
    # Stores sealed before sharding must keep reading, and keep their stamped digest.
    assert store_digest(instance) == sharded
    with materialize_mutant_sources(instance, "repo_10") as repo:
        assert (repo / "tool.c").read_text() == "mutant B"


def test_resolve_implementation_dir_appends_the_instance_to_a_local_path(tmp_path) -> None:
    assert resolve_implementation_dir(str(tmp_path), "org__tool.abc123") == tmp_path / "org__tool.abc123"
