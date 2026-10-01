from __future__ import annotations

from pathlib import Path

from programbench.utils.mutant_store import resolve_mutants_dir


def test_resolve_mutants_dir_returns_local_path_unchanged(tmp_path):
    local = tmp_path / "mutants"
    assert resolve_mutants_dir(str(local), "some__instance.abc123") == local


def test_resolve_mutants_dir_downloads_from_huggingface(monkeypatch, tmp_path):
    calls = []

    def fake_snapshot_download(repo_id, *, repo_type, revision, allow_patterns):
        calls.append((repo_id, repo_type, revision, allow_patterns))
        return str(tmp_path)

    monkeypatch.setattr("huggingface_hub.snapshot_download", fake_snapshot_download)

    result = resolve_mutants_dir("hf://org/pb-mutant-store@v2", "some__instance.abc123")

    assert result == tmp_path
    assert calls == [
        (
            "org/pb-mutant-store",
            "dataset",
            "v2",
            ["some__instance.abc123/mutants.json", "some__instance.abc123/.artifacts/sha256/**"],
        )
    ]


def test_resolve_mutants_dir_defaults_to_main_revision(monkeypatch, tmp_path):
    def fake_snapshot_download(repo_id, *, repo_type, revision, allow_patterns):
        assert repo_id == "org/pb-mutant-store"
        assert revision == "main"
        return str(tmp_path)

    monkeypatch.setattr("huggingface_hub.snapshot_download", fake_snapshot_download)

    assert resolve_mutants_dir("hf://org/pb-mutant-store", "iid") == tmp_path


def test_resolve_mutants_dir_fetches_sealed_sources_for_attribution(monkeypatch, tmp_path):
    calls = []

    def fake_snapshot_download(repo_id, *, repo_type, revision, allow_patterns):
        calls.append(allow_patterns)
        return str(tmp_path)

    monkeypatch.setattr("huggingface_hub.snapshot_download", fake_snapshot_download)

    assert resolve_mutants_dir("hf://org/pb-mutants", "iid", with_sources=True) == tmp_path
    assert calls == [
        [
            "iid/mutants.json",
            "iid/.artifacts/sha256/**",
            "iid/sources.json",
            "iid/.artifacts/sources/**",
        ]
    ]
