"""Compact, content-addressed storage for mutant suites."""

from __future__ import annotations

import errno
import gzip
import hashlib
import json
import os
import shutil
import stat
import tempfile
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterator


ARTIFACT_DIR = ".artifacts/sha256"
MANIFEST_NAME = "mutants.json"
_CHUNK_SIZE = 1024 * 1024


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(_CHUNK_SIZE):
            digest.update(chunk)
    return digest.hexdigest()


def _atomic_json_write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "w") as output:
            json.dump(value, output, indent=2, sort_keys=True)
            output.write("\n")
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def _store_executable(instance_root: Path, executable: Path) -> dict[str, Any]:
    digest = file_sha256(executable)
    artifact = instance_root / ARTIFACT_DIR / f"{digest}.gz"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    if not artifact.is_file():
        fd, temporary_name = tempfile.mkstemp(prefix=f".{digest}.", dir=artifact.parent)
        temporary = Path(temporary_name)
        try:
            with os.fdopen(fd, "wb") as raw_output:
                with gzip.GzipFile(fileobj=raw_output, mode="wb", filename="", mtime=0) as output:
                    with executable.open("rb") as source:
                        shutil.copyfileobj(source, output, length=_CHUNK_SIZE)
            temporary.replace(artifact)
        finally:
            temporary.unlink(missing_ok=True)
    result = {
        "sha256": digest,
        "compression": "gzip",
        "path": artifact.relative_to(instance_root).as_posix(),
        "size": executable.stat().st_size,
    }
    executable.unlink()
    return result


def compact_mutant_suite(instance_root: Path) -> dict[str, Any]:
    """Move executable payloads into a compressed SHA-256 store.

    The legacy ``payload`` field remains in the manifest so source-oriented
    tools can still locate ``repo_N`` via its parent. Evaluation resolves the
    new ``artifact`` field when the legacy executable is absent.
    """

    manifest_path = instance_root / MANIFEST_NAME
    if not manifest_path.is_file():
        return {"compacted": 0, "artifacts": 0}
    manifest = json.loads(manifest_path.read_text())
    mutants = manifest.get("mutants", []) if isinstance(manifest, dict) else []
    compacted = 0
    for mutant in mutants:
        if not isinstance(mutant, dict):
            continue
        payload = instance_root / str(mutant.get("payload", ""))
        if payload.is_file():
            mutant["artifact"] = _store_executable(instance_root, payload)
            compacted += 1
    if compacted:
        _atomic_json_write(manifest_path, manifest)

    referenced_artifacts = {
        str(mutant.get("artifact", {}).get("path", ""))
        for mutant in mutants
        if isinstance(mutant, dict) and isinstance(mutant.get("artifact"), dict)
    }
    artifact_root = instance_root / ARTIFACT_DIR
    for artifact in artifact_root.glob("*.gz"):
        relative_path = artifact.relative_to(instance_root).as_posix()
        if relative_path not in referenced_artifacts:
            artifact.unlink()

    artifacts = len(list(artifact_root.glob("*.gz")))
    return {"compacted": compacted, "artifacts": artifacts}


def mutant_store_state(instance_root: Path) -> str:
    """Classify a mutant store by whether every executable payload resolves.

    Evaluation reads ``payload`` and falls back to ``artifact``, so that pair is
    what "built" means here. "unbuilt" is the recoverable crash state: manifests
    and repo_N sources exist but the executables never reached the host, so
    compiling the sources is enough and the generation agent need not rerun.
    """

    manifest = instance_root / MANIFEST_NAME
    if not manifest.is_file():
        return "missing"
    mutants = json.loads(manifest.read_text())["mutants"]
    if all(
        (instance_root / mutant["payload"]).is_file()
        or ("artifact" in mutant and (instance_root / mutant["artifact"]["path"]).is_file())
        for mutant in mutants
    ):
        return "ready"
    return "unbuilt"


@contextmanager
def materialize_mutant_payload(instance_root: Path, mutant: Any) -> Iterator[Path]:
    """Yield an executable path for a legacy or compact mutant payload."""

    payload = instance_root / mutant.payload
    if payload.is_file():
        yield payload
        return

    artifact = getattr(mutant, "artifact", None)
    if artifact is None:
        raise FileNotFoundError(payload)
    if artifact.compression != "gzip":
        raise ValueError(f"Unsupported mutant artifact compression: {artifact.compression}")
    source = instance_root / artifact.path
    if not source.is_file():
        raise FileNotFoundError(source)

    fd, temporary_name = tempfile.mkstemp(prefix=f"programbench-mutant-{mutant.id}-")
    os.close(fd)
    temporary = Path(temporary_name)
    try:
        with gzip.open(source, "rb") as compressed, temporary.open("wb") as output:
            shutil.copyfileobj(compressed, output, length=_CHUNK_SIZE)
        actual = file_sha256(temporary)
        if actual != artifact.sha256:
            raise RuntimeError(
                f"Mutant artifact hash mismatch for {mutant.id}: expected {artifact.sha256}, got {actual}"
            )
        temporary.chmod(temporary.stat().st_mode | stat.S_IXUSR)
        yield temporary
    finally:
        temporary.unlink(missing_ok=True)


def deduplicate_mutant_files(instance_root: Path, *reference_roots: Path) -> dict[str, int]:
    """Hardlink byte-identical regular files in and across immutable suites."""

    canonical: dict[tuple[int, int, str], Path] = {}
    linked = 0
    saved = 0

    def visit(root: Path, *, replace: bool) -> None:
        nonlocal linked, saved
        if not root.is_dir():
            return
        for path in sorted(root.rglob("*")):
            if path.is_symlink() or not path.is_file():
                continue
            file_stat = path.stat()
            mode = stat.S_IMODE(file_stat.st_mode)
            digest = file_sha256(path)
            key = (file_stat.st_size, mode, digest)
            existing = canonical.get(key)
            if existing is None:
                canonical[key] = path
                continue
            existing_stat = existing.stat()
            if existing_stat.st_dev == file_stat.st_dev and existing_stat.st_ino == file_stat.st_ino:
                continue
            if not replace or existing_stat.st_dev != file_stat.st_dev:
                continue
            temporary = path.with_name(f".{path.name}.dedupe-{os.getpid()}")
            temporary.unlink(missing_ok=True)
            try:
                os.link(existing, temporary)
                temporary.replace(path)
            except OSError as error:
                if error.errno != errno.EMLINK:
                    raise
                # The canonical inode reached the filesystem link limit; restart the
                # chain from this copy so the remaining duplicates still deduplicate.
                canonical[key] = path
                continue
            finally:
                temporary.unlink(missing_ok=True)
            linked += 1
            saved += file_stat.st_size

    for reference in reference_roots:
        visit(reference, replace=False)
    visit(instance_root, replace=True)
    return {"linked": linked, "saved_bytes": saved}


def hardlink_or_copy(source: str, destination: str) -> str:
    """``copy_function`` for copytree with a cross-filesystem fallback."""

    try:
        os.link(source, destination)
        return destination
    except OSError:
        return shutil.copy2(source, destination)


SOURCE_ARTIFACT_DIR = ".artifacts/sources"
SOURCES_MANIFEST = "sources.json"
DIGEST_FILE = "digest"

# repo_N trees are compiled in place, so build output sits beside the sources. It is
# host-specific and dwarfs the sources (780 MiB vs 92 MiB per ffmpeg repo).
SKIPPED_SOURCE_DIRS = {"build", "target", ".git", "node_modules"}
SKIPPED_SOURCE_SUFFIXES = {".o", ".a", ".d", ".so", ".lo", ".obj", ".lib", ".dylib", ".pyc", ".rlib", ".rmeta"}
ELF_MAGIC = b"\x7fELF"


def source_blob_name(digest: str) -> str:
    """Path of a source blob, sharded because the Hub caps a directory at 10k files."""

    return f"{SOURCE_ARTIFACT_DIR}/{digest[:2]}/{digest}.gz"


def source_blob_path(instance_root: Path, digest: str) -> Path:
    blob = instance_root / source_blob_name(digest)
    # Stores sealed before sharding hold every blob directly under SOURCE_ARTIFACT_DIR.
    return blob if blob.is_file() else instance_root / SOURCE_ARTIFACT_DIR / f"{digest}.gz"


def iter_source_blobs(instance_root: Path) -> list[Path]:
    """Every blob of either layout, name-ordered so the layout cannot alter a digest."""

    return sorted((instance_root / SOURCE_ARTIFACT_DIR).rglob("*.gz"), key=lambda blob: blob.name)


def tracked_sources(root: Path) -> dict[str, tuple[Path, str]]:
    """Map repo-relative path to (file, digest) for everything worth preserving."""

    tracked = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        relative = path.relative_to(root)
        if not SKIPPED_SOURCE_DIRS.isdisjoint(relative.parts) or path.suffix in SKIPPED_SOURCE_SUFFIXES:
            continue
        # Linked binaries (ffmpeg, ffmpeg_g, a.out) carry no suffix; ELF magic is the only tell.
        if not path.suffix:
            with path.open("rb") as handle:
                if handle.read(4) == ELF_MAGIC:
                    continue
        tracked[relative.as_posix()] = (path, file_sha256(path))
    return tracked


def sources_digest(sources: dict[str, str]) -> str:
    """Digest a {relative path: file digest} map into one tree identity."""

    digest = hashlib.sha256()
    for relative, file_digest in sorted(sources.items()):
        digest.update(f"{relative}\0{file_digest}\0".encode())
    return digest.hexdigest()


@lru_cache(maxsize=None)
def ground_truth_digest(root: Path, removed: frozenset[str] = frozenset()) -> str:
    """Identify the part of a ground-truth tree that rebuilt mutants inherit.

    Files the suite deletes everywhere are excluded: they never reach a rebuilt
    repo, so a base tree that merely lacks them (a HuggingFace archive predating
    the reference build's stamp, say) still rebuilds byte-identical sources.
    Cached because rebuilding otherwise rehashes the whole tree per mutant.
    """

    return sources_digest(
        {relative: digest for relative, (_, digest) in tracked_sources(root).items() if relative not in removed}
    )


def _store_source_blob(instance_root: Path, source: Path, digest: str) -> None:
    if source_blob_path(instance_root, digest).is_file():
        return
    blob = instance_root / source_blob_name(digest)
    blob.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=f".{digest}.", dir=blob.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "wb") as raw_output:
            with gzip.GzipFile(fileobj=raw_output, mode="wb", filename="", mtime=0) as output:
                with source.open("rb") as raw_source:
                    shutil.copyfileobj(raw_source, output, length=_CHUNK_SIZE)
        temporary.replace(blob)
    finally:
        temporary.unlink(missing_ok=True)


def seal_mutant_sources(instance_root: Path, ground_truth: Path) -> dict[str, Any]:
    """Replace repo_N trees with the information needed to rebuild them.

    Each repo_N is a near-complete copy of ``ground_truth``, so only files that
    differ from it are kept, each unique content exactly once. Sharing between
    mutants is heavy but partial -- ffmpeg's 85 differing paths are dominated by
    build output identical in all 100 repos, while cmatrix's 34 copies of
    cmatrix.c hold 4 distinct contents -- so the blobs are content-addressed
    rather than filed per repo.
    """

    base = {relative: digest for relative, (_, digest) in tracked_sources(ground_truth).items()}
    repos = sorted(
        (repo for repo in instance_root.glob("repo_*") if repo.is_dir()),
        key=lambda repo: (len(repo.name), repo.name),
    )
    overlays: dict[str, dict[str, str]] = {}
    present: set[str] = set()
    for repo in repos:
        tracked = tracked_sources(repo)
        present.update(tracked)
        overlay = {}
        for relative, (path, digest) in sorted(tracked.items()):
            if base.get(relative) == digest:
                continue
            overlay[relative] = digest
            _store_source_blob(instance_root, path, digest)
        overlays[repo.name] = overlay

    _atomic_json_write(
        instance_root / SOURCES_MANIFEST,
        {
            "instance_id": instance_root.name,
            "compression": "gzip",
            # Recorded so rebuilding a repo needs nothing but the store itself.
            "ground_truth": ground_truth.as_posix(),
            # Overlays only name the files that differ, so every other file is
            # taken from the base tree on trust. Pin its identity to catch a
            # substituted tree instead of rebuilding the wrong sources in silence.
            "base_digest": sources_digest(
                {relative: digest for relative, digest in base.items() if relative in present}
            ),
            "overlays": overlays,
            "removed": sorted(set(base) - present),
        },
    )
    for repo in repos:
        shutil.rmtree(repo)
    return {
        "repos": len(repos),
        "blobs": len(iter_source_blobs(instance_root)),
        "overlay_entries": sum(len(overlay) for overlay in overlays.values()),
    }


@contextmanager
def materialize_mutant_sources(
    instance_root: Path, mutant_id: str, ground_truth: Path | None = None
) -> Iterator[Path]:
    """Yield a rebuilt repo_N tree for a legacy or sealed mutant suite."""

    legacy = instance_root / mutant_id
    if legacy.is_dir():
        yield legacy
        return

    manifest = json.loads((instance_root / SOURCES_MANIFEST).read_text())
    ground_truth = ground_truth or Path(manifest["ground_truth"])
    overlay = manifest["overlays"][mutant_id]
    if not ground_truth.is_dir():
        # Without this the digest check below reports a mismatch, which reads as
        # a substituted tree rather than a missing one.
        raise FileNotFoundError(
            f"Ground-truth tree for {instance_root.name} does not exist: {ground_truth}. "
            "Sealed mutant sources are an overlay on it; pass a path or hf://<repo_id>[@revision] "
            "via --ground-truth-dir to rebuild them from elsewhere."
        )
    # Absent only in stores sealed before base_digest existed, which stay usable.
    expected_digest = manifest.get("base_digest")
    removed = frozenset(manifest["removed"])
    if expected_digest is not None and ground_truth_digest(ground_truth, removed) != expected_digest:
        raise ValueError(
            f"Ground-truth tree does not match the one {instance_root.name} was sealed against: "
            f"{ground_truth}. Mutant sources are an overlay on that tree and cannot be rebuilt from another."
        )
    with tempfile.TemporaryDirectory(prefix=f"programbench-mutant-source-{mutant_id}-") as temporary:
        repo = Path(temporary) / mutant_id
        shutil.copytree(ground_truth, repo, symlinks=True, copy_function=hardlink_or_copy)
        for relative in removed:
            (repo / relative).unlink(missing_ok=True)
        for relative, digest in overlay.items():
            target = repo / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            # The tree is hardlinked from the ground truth, so replace the link
            # rather than writing through it and corrupting the shared original.
            target.unlink(missing_ok=True)
            with gzip.open(source_blob_path(instance_root, digest), "rb") as blob:
                with target.open("wb") as output:
                    shutil.copyfileobj(blob, output, length=_CHUNK_SIZE)
        yield repo


def seal_mutant_store(instance_root: Path, ground_truth: Path) -> dict[str, Any]:
    """Compact executables and sources, then stamp the store's digest.

    The sealed store is what every iteration shares, so the digest is recorded
    once here instead of being recomputed from a 1.6M-file tree per iteration.
    """

    status = compact_mutant_suite(instance_root)
    status.update(seal_mutant_sources(instance_root, ground_truth))
    (instance_root / DIGEST_FILE).write_text(f"{store_digest(instance_root)}\n")
    return status


def store_digest(instance_root: Path) -> str:
    """Digest the manifests and artifact names that define a sealed store."""

    digest = hashlib.sha256()
    for name in (MANIFEST_NAME, SOURCES_MANIFEST):
        manifest = instance_root / name
        digest.update(manifest.read_bytes() if manifest.is_file() else b"")
    for artifact in sorted((instance_root / ARTIFACT_DIR).glob("*.gz")):
        digest.update(artifact.name.encode())
    for blob in iter_source_blobs(instance_root):
        digest.update(blob.name.encode())
    return digest.hexdigest()
