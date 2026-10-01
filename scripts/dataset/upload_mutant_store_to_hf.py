#!/usr/bin/env python3
"""Upload a compact mutant store to HuggingFace so eval-tests can use it remotely.

Source layout (as produced by generate-mutants / the iterative pipeline, e.g.
``output/debug_iterative_v34/iter_5/mutant``)::

    <source>/<instance_id>/mutants.json
    <source>/<instance_id>/.artifacts/sha256/<sha256>.gz
    <source>/<instance_id>/repo_N/<mutated sources>   # unsealed suites only

The manifest and the content-addressed executable artifacts it references are
uploaded verbatim, so ``programbench eval-tests --mutants-dir
hf://<repo_id>[@revision]`` downloads exactly those back with
``huggingface_hub.snapshot_download``.

Every repo_N is a near-complete copy of the ground-truth tree, so uploading them
whole is wildly redundant (9.9 GiB for 100 ffmpeg mutants). Instead the sources go
up as an overlay over ``ground_truth/implementation/<instance_id>``: only files
that differ from it are stored, each unique content exactly once::

    <instance_id>/sources.json                          # base reference, per-repo path -> sha256, removed paths
    <instance_id>/.artifacts/sources/<sha[:2]>/<sha>.gz # one blob per unique file content

Content-addressing rather than a per-repo directory matters because the overlay
shares heavily but only partially: ffmpeg's 85 differing paths are dominated by
build output identical in all 100 repos, while cmatrix's 34 copies of ``cmatrix.c``
hold just 4 distinct contents. That takes ffmpeg from 9.9 GiB to 8 MiB and cmatrix
from 11.1 MiB to 0.2 MiB.

This is the same on-disk layout ``programbench seal-mutants`` produces, so a sealed
store uploads as-is; an unsealed one is sealed into a staging copy first. Restore a
mutant tree with ``programbench.mutant_storage.materialize_mutant_sources`` after
extracting ``implementation/<instance_id>.tar.gz`` from the ground-truth dataset.
Pass ``--no-sources`` to upload only what eval-tests needs.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import tempfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

from programbench.mutant_storage import (
    ARTIFACT_DIR,
    MANIFEST_NAME,
    SOURCE_ARTIFACT_DIR,
    SOURCES_MANIFEST,
    hardlink_or_copy,
    iter_source_blobs,
    seal_mutant_sources,
    source_blob_name,
)

# The Hub rejects a commit that would put more than 10k files in one directory, which
# universal-ctags' 10212 source blobs do, so blobs always upload under their shard even
# when the local store predates sharding.
FLAT_BLOB_RE = re.compile(rf"^(?P<instance>[^/]+)/{re.escape(SOURCE_ARTIFACT_DIR)}/(?P<digest>[0-9a-f]+)\.gz$")


DEFAULT_SOURCE = Path("output/mutants")
DEFAULT_GROUND_TRUTH = Path("ground_truth/implementation")


@dataclass
class InstanceUpload:
    instance_id: str
    manifest_path: Path
    artifact_paths: list[Path]
    # (path within the instance directory on the Hub, local file to upload)
    source_files: list[tuple[str, Path]] = field(default_factory=list)

    @property
    def upload_files(self) -> list[tuple[str, Path]]:
        return [
            (MANIFEST_NAME, self.manifest_path),
            *((f"{ARTIFACT_DIR}/{artifact.name}", artifact) for artifact in self.artifact_paths),
            *self.source_files,
        ]

    @property
    def total_size(self) -> int:
        return sum(path.stat().st_size for _, path in self.upload_files)

    @property
    def source_size(self) -> int:
        return sum(path.stat().st_size for _, path in self.source_files)


def _sealed_source_files(instance_dir: Path) -> list[tuple[str, Path]]:
    return [
        (SOURCES_MANIFEST, instance_dir / SOURCES_MANIFEST),
        *((source_blob_name(blob.stem), blob) for blob in iter_source_blobs(instance_dir)),
    ]


def _instance_upload(instance_dir: Path, ground_truth_dir: Path | None, staging: Path) -> InstanceUpload | None:
    manifest_path = instance_dir / MANIFEST_NAME
    if not manifest_path.is_file():
        return None
    upload = InstanceUpload(
        instance_id=instance_dir.name,
        manifest_path=manifest_path,
        artifact_paths=sorted((instance_dir / ARTIFACT_DIR).glob("*.gz")),
    )
    if ground_truth_dir is None:
        return upload
    if (instance_dir / SOURCES_MANIFEST).is_file():
        upload.source_files = _sealed_source_files(instance_dir)
        return upload
    # An unsealed suite still holds repo_N trees; seal a copy into staging so the
    # uploaded layout is identical either way.
    sealed = staging / instance_dir.name
    sealed.mkdir(parents=True)
    for repo in instance_dir.glob("repo_*"):
        if repo.is_dir():
            shutil.copytree(repo, sealed / repo.name, symlinks=True, copy_function=hardlink_or_copy)
    seal_mutant_sources(sealed, ground_truth_dir / instance_dir.name)
    upload.source_files = _sealed_source_files(sealed)
    return upload


def _iter_selected(
    source: Path,
    filter_re: re.Pattern[str] | None,
    ground_truth_dir: Path | None,
    staging: Path,
    workers: int,
) -> list[InstanceUpload]:
    if not source.is_dir():
        raise SystemExit(f"source directory does not exist: {source}")
    candidates = [
        instance_dir
        for instance_dir in sorted(source.iterdir())
        if instance_dir.is_dir() and (filter_re is None or filter_re.search(instance_dir.name))
    ]
    # Sealing an unsealed suite is the expensive part (copy every repo_N, hash and
    # gzip what differs); hashlib and zlib drop the GIL, so threads actually help.
    with ThreadPoolExecutor(max_workers=workers) as executor:
        prepared = dict(
            zip(
                candidates,
                executor.map(lambda d: _instance_upload(d, ground_truth_dir, staging), candidates),
            )
        )
    return [upload for upload in prepared.values() if upload is not None]


def _format_size(num_bytes: int) -> str:
    value = float(num_bytes)
    for unit in ("B", "KiB", "MiB", "GiB"):
        if value < 1024 or unit == "GiB":
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024
    return f"{num_bytes} B"


def _commit_batch(
    *,
    repo_id: str,
    repo_type: str,
    revision: str,
    commit_message: str,
    token: str | None,
    batch: list[tuple[str, Path]],
) -> str:
    from huggingface_hub import CommitOperationAdd, HfApi

    info = HfApi(token=token).create_commit(
        repo_id=repo_id,
        repo_type=repo_type,
        revision=revision,
        operations=[
            CommitOperationAdd(path_in_repo=path_in_repo, path_or_fileobj=str(path))
            for path_in_repo, path in batch
        ],
        commit_message=f"{commit_message}: {len(batch)} files",
    )
    return str(info.commit_url)


def _repo_files(*, repo_id: str, repo_type: str, revision: str, token: str | None) -> set[str]:
    from huggingface_hub import HfApi

    remote = set(HfApi(token=token).list_repo_files(repo_id=repo_id, repo_type=repo_type, revision=revision))
    # A blob uploaded before sharding already satisfies its sharded path -- readers
    # resolve either layout -- so it must not be re-uploaded under the new name.
    return remote | {
        f"{match['instance']}/{source_blob_name(match['digest'])}"
        for match in map(FLAT_BLOB_RE.match, remote)
        if match
    }


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return parsed


def _resolve_repo_id(repo_id: str, token: str | None) -> str:
    """Prepend the authenticated user's namespace when repo_id has none.

    HfApi.create_repo() silently namespaces a bare repo_id under the caller,
    but create_commit()/preupload_lfs_files() resolve a bare repo_id literally
    and 404. Resolving the namespace once keeps every call consistent.
    """
    if "/" in repo_id:
        return repo_id
    from huggingface_hub import HfApi

    return f'{HfApi(token=token).whoami()["name"]}/{repo_id}'


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--source",
        type=Path,
        default=DEFAULT_SOURCE,
        help="Mutants directory containing <instance_id>/mutants.json, e.g. output/debug_iterative_v34/iter_5/mutant.",
    )
    parser.add_argument("--repo-id", default="eth-sri/tsb-mutants", help="HuggingFace dataset repo id.")
    parser.add_argument("--repo-type", default="dataset", help="HuggingFace repo type.")
    parser.add_argument("--revision", default="main", help="Target branch/revision.")
    parser.add_argument("--filter", default="", help="Regex selecting instance IDs to upload.")
    parser.add_argument(
        "--ground-truth-dir",
        type=Path,
        default=DEFAULT_GROUND_TRUTH,
        help="Ground-truth implementations the repo_N sources are diffed against.",
    )
    parser.add_argument(
        "--no-sources",
        dest="sources",
        action="store_false",
        help="Upload only mutants.json and the executable artifacts, skipping the mutant source overlay.",
    )
    parser.add_argument("--token", default=os.environ.get("HF_TOKEN"), help="HF token; defaults to HF_TOKEN.")
    parser.add_argument("--commit-message", default="Add ProgramBench mutant store", help="Commit message prefix.")
    parser.add_argument("--create-repo", action="store_true", help="Create the HF repo if it does not already exist.")
    parser.add_argument("--private", action="store_true", help="Create the repo as private when used with --create-repo.")
    parser.add_argument("--workers", type=_positive_int, default=8, help="Concurrent instance preparation workers (default: 8).")
    parser.add_argument("--batch-size", type=_positive_int, default=200, help="Files per Hub commit (default: 200).")
    parser.add_argument("--force", action="store_true", help="Upload paths that already exist in the repository.")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be uploaded without committing.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    with tempfile.TemporaryDirectory(prefix="programbench-mutant-sources-") as staging:
        _run(args, Path(staging))


def _run(args: argparse.Namespace, staging: Path) -> None:
    selected = _iter_selected(
        args.source,
        re.compile(args.filter) if args.filter else None,
        args.ground_truth_dir if args.sources else None,
        staging,
        args.workers,
    )
    if not selected:
        raise SystemExit("no instance mutants.json manifests found under source")

    print(
        f"Selected {len(selected)} instance(s), "
        f"{sum(len(upload.artifact_paths) for upload in selected)} mutant artifact(s), "
        f"{sum(len(upload.source_files) for upload in selected)} source file(s), "
        f"{_format_size(sum(upload.total_size for upload in selected))}."
    )
    if args.dry_run:
        for upload in selected:
            print(
                f"DRY-RUN {upload.instance_id}: {len(upload.artifact_paths)} artifact(s) "
                f"+ {len(upload.source_files)} source file(s) ({_format_size(upload.source_size)}), "
                f"{_format_size(upload.total_size)} total"
            )
        return

    from huggingface_hub.utils import disable_progress_bars

    disable_progress_bars()

    repo_id = _resolve_repo_id(args.repo_id, args.token)
    if repo_id != args.repo_id:
        print(f"Resolved repo id {args.repo_id!r} to {repo_id!r} (no namespace given)")

    if args.create_repo:
        from huggingface_hub import HfApi

        HfApi(token=args.token).create_repo(
            repo_id=repo_id,
            repo_type=args.repo_type,
            private=args.private,
            exist_ok=True,
        )

    files = [
        (f"{upload.instance_id}/{name}", path)
        for upload in selected
        for name, path in upload.upload_files
    ]
    if not args.force:
        remote = _repo_files(
            repo_id=repo_id, repo_type=args.repo_type, revision=args.revision, token=args.token
        )
        pending = [entry for entry in files if entry[0] not in remote]
        if len(pending) < len(files):
            print(f"Skipping {len(files) - len(pending)} file(s) already present in {repo_id}@{args.revision}.")
        files = pending

    batch_count = (len(files) + args.batch_size - 1) // args.batch_size
    for index, start in enumerate(range(0, len(files), args.batch_size), start=1):
        batch = files[start : start + args.batch_size]
        commit_url = _commit_batch(
            repo_id=repo_id,
            repo_type=args.repo_type,
            revision=args.revision,
            commit_message=args.commit_message,
            token=args.token,
            batch=batch,
        )
        print(
            f"[{index}/{batch_count}] committed {len(batch)} file(s) "
            f"({_format_size(sum(path.stat().st_size for _, path in batch))})\n  {commit_url}",
            flush=True,
        )


if __name__ == "__main__":
    main()
