from __future__ import annotations

import errno
import json
import os
from pathlib import Path

import pytest

from programbench.mutant_storage import (
    compact_mutant_suite,
    deduplicate_mutant_files,
    materialize_mutant_payload,
    mutant_store_state,
)
from programbench.mutants import load_mutant_suite


def _write_suite(root: Path, task: str) -> Path:
    instance = root / task
    mutants = []
    for name in ("repo_1", "repo_2"):
        repo = instance / name
        repo.mkdir(parents=True)
        (repo / "source.c").write_text("int main(void) { return 0; }\n")
        executable = repo / "executable"
        executable.write_bytes(b"#!/bin/sh\nexit 7\n" + b"x" * 4096)
        executable.chmod(0o755)
        mutants.append(
            {
                "id": name,
                "kind": "wrapper",
                "payload": f"{name}/executable",
            }
        )
    (instance / "mutants.json").write_text(
        json.dumps({"instance_id": task, "mutants": mutants})
    )
    return instance


def test_compact_suite_deduplicates_and_materializes_executables(tmp_path: Path) -> None:
    task = "org__repo.rev"
    instance = _write_suite(tmp_path, task)
    stale_artifact = instance / ".artifacts" / "sha256" / ("0" * 64 + ".gz")
    stale_artifact.parent.mkdir(parents=True)
    stale_artifact.write_bytes(b"stale")

    result = compact_mutant_suite(instance)

    assert result == {"compacted": 2, "artifacts": 1}
    assert not stale_artifact.exists()
    assert not (instance / "repo_1" / "executable").exists()
    loaded = load_mutant_suite(tmp_path, task)
    assert loaded is not None
    instance_root, suite = loaded
    assert suite.mutants[0].artifact is not None
    assert suite.mutants[0].artifact.sha256 == suite.mutants[1].artifact.sha256
    with materialize_mutant_payload(instance_root, suite.mutants[0]) as payload:
        assert payload.read_bytes() == b"#!/bin/sh\nexit 7\n" + b"x" * 4096
        assert os.access(payload, os.X_OK)
    assert not payload.exists()


def test_deduplicate_mutant_files_hardlinks_identical_sources(tmp_path: Path) -> None:
    instance = _write_suite(tmp_path, "org__repo.rev")

    result = deduplicate_mutant_files(instance)

    first = instance / "repo_1" / "source.c"
    second = instance / "repo_2" / "source.c"
    assert first.stat().st_ino == second.stat().st_ino
    assert result["linked"] >= 1
    assert result["saved_bytes"] >= first.stat().st_size


def test_deduplicate_mutant_files_survives_the_filesystem_link_limit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    instance = _write_suite(tmp_path, "org__repo.rev")
    real_link = os.link

    def link(source, destination):
        if Path(source).name == "executable":
            raise OSError(errno.EMLINK, "Too many links")
        return real_link(source, destination)

    monkeypatch.setattr(os, "link", link)

    result = deduplicate_mutant_files(instance)

    # The capped inode is left alone and intact; unrelated duplicates still link.
    executables = [instance / name / "executable" for name in ("repo_1", "repo_2")]
    assert executables[0].stat().st_ino != executables[1].stat().st_ino
    assert executables[1].read_bytes() == executables[0].read_bytes()
    assert result["linked"] == 1
    assert (instance / "repo_1" / "source.c").stat().st_ino == (
        instance / "repo_2" / "source.c"
    ).stat().st_ino


def test_mutant_store_state_follows_the_payload_lifecycle(tmp_path: Path) -> None:
    task = "org__repo.rev"
    instance = _write_suite(tmp_path, task)
    assert mutant_store_state(tmp_path / "absent") == "missing"
    assert mutant_store_state(instance) == "ready"

    # The crash this guards: generation wrote the manifest, then died before the
    # executables were copied out of the build container.
    (instance / "repo_1" / "executable").unlink()
    assert mutant_store_state(instance) == "unbuilt"
    assert (instance / "repo_1" / "source.c").is_file()

    (instance / "repo_1" / "executable").write_bytes(b"#!/bin/sh\nexit 7\n" + b"x" * 4096)
    compact_mutant_suite(instance)
    # Compaction legitimately removes every repo_N/executable, so a store that
    # resolves only through .artifacts must not read as unbuilt and be rebuilt.
    assert not list(instance.glob("repo_*/executable"))
    assert mutant_store_state(instance) == "ready"

    next(iter((instance / ".artifacts" / "sha256").glob("*.gz"))).unlink()
    assert mutant_store_state(instance) == "unbuilt"
