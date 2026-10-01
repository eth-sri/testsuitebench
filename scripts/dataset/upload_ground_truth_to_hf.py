#!/usr/bin/env python3
"""Upload ground_truth (executables and/or implementations) to HuggingFace.

Source layout (as produced by reference_test_preparation.py)::

    <source>/executable/<instance_id>/executable
    <source>/implementation/<instance_id>/...

Executables are uploaded as-is, one per instance, so eval and eval-tests can
download just what they need with
``huggingface_hub.snapshot_download(allow_patterns=f"executable/{instance_id}/**")``
(see ``programbench.utils.ground_truth_store.resolve_ground_truth_dir``, used
via ``--ground-truth-dir hf://<repo_id>[@revision]``).

Implementations are full source trees, so each is archived as
``implementation/<instance_id>.tar.gz`` to keep the number of uploaded files
manageable; extract it locally to restore
``ground_truth/implementation/<instance_id>/``.
"""

from __future__ import annotations

import argparse
import gzip
import os
import re
import sys
import tarfile
import tempfile
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path


DEFAULT_SOURCE = Path("ground_truth")


@dataclass(frozen=True)
class PreparedUpload:
    kind: str
    instance_id: str
    path_in_repo: str
    local_path: Path
    size: int


def _reset_tarinfo(info: tarfile.TarInfo) -> tarfile.TarInfo:
    info.uid = 0
    info.gid = 0
    info.uname = ""
    info.gname = ""
    return info


def _archive_implementation(implementation_dir: Path, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as gz:
            with tarfile.open(fileobj=gz, mode="w") as tar:
                tar.add(implementation_dir, arcname=".", recursive=True, filter=_reset_tarinfo)
    return dest


def _format_size(num_bytes: int) -> str:
    value = float(num_bytes)
    for unit in ("B", "KiB", "MiB", "GiB"):
        if value < 1024 or unit == "GiB":
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024
    return f"{num_bytes} B"


def _warn_failed(kind: str, instance_id: str, error: Exception) -> None:
    print(
        f"WARNING: skipping {kind}/{instance_id} after {type(error).__name__}: {error}",
        file=sys.stderr,
    )


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return parsed


def _instance_ids(source: Path, part: str, filter_re: re.Pattern[str] | None) -> list[str]:
    part_dir = source / part
    if not part_dir.is_dir():
        return []
    ids = [path.name for path in sorted(part_dir.iterdir()) if path.is_dir()]
    if filter_re is not None:
        ids = [iid for iid in ids if filter_re.search(iid)]
    return ids


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


def _disable_hf_progress_bars() -> None:
    from huggingface_hub.utils import disable_progress_bars

    disable_progress_bars()


def _repo_files(*, repo_id: str, repo_type: str, revision: str, token: str | None) -> set[str]:
    from huggingface_hub import HfApi

    return set(
        HfApi(token=token).list_repo_files(
            repo_id=repo_id,
            repo_type=repo_type,
            revision=revision,
        )
    )


def _prepare_one(
    *,
    kind: str,
    instance_id: str,
    source: Path,
    tmp_root: Path,
) -> PreparedUpload:
    if kind == "executable":
        path_in_repo = f"executable/{instance_id}/executable"
        local_path = source / path_in_repo
        return PreparedUpload(kind, instance_id, path_in_repo, local_path, local_path.stat().st_size)

    path_in_repo = f"implementation/{instance_id}.tar.gz"
    archive_path = tmp_root / f"{instance_id}.tar.gz"
    _archive_implementation(source / "implementation" / instance_id, archive_path)
    return PreparedUpload(kind, instance_id, path_in_repo, archive_path, archive_path.stat().st_size)


def _commit_batch(
    *,
    uploads: list[PreparedUpload],
    repo_id: str,
    repo_type: str,
    revision: str,
    commit_message: str,
    token: str | None,
) -> None:
    from huggingface_hub import CommitOperationAdd, HfApi

    operations = [
        CommitOperationAdd(path_in_repo=upload.path_in_repo, path_or_fileobj=str(upload.local_path))
        for upload in uploads
    ]
    HfApi(token=token).create_commit(
        repo_id=repo_id,
        repo_type=repo_type,
        revision=revision,
        operations=operations,
        commit_message=f"{commit_message}: {len(uploads)} artifacts",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE, help="ground_truth directory.")
    parser.add_argument(
        "--include",
        choices=("executable", "implementation", "both"),
        default="both",
        help="Which part(s) to upload.",
    )
    parser.add_argument("--repo-id", default="eth-sri/tsb-reference_impl", help="HuggingFace dataset repo id.")
    parser.add_argument("--repo-type", default="dataset", help="HuggingFace repo type.")
    parser.add_argument("--revision", default="main", help="Target branch/revision.")
    parser.add_argument("--filter", default="", help="Regex selecting instance IDs to upload.")
    parser.add_argument("--token", default=os.environ.get("HF_TOKEN"), help="HF token; defaults to HF_TOKEN.")
    parser.add_argument("--commit-message", default="Add ProgramBench ground truth", help="Commit message prefix.")
    parser.add_argument("--create-repo", action="store_true", help="Create the HF repo if it does not already exist.")
    parser.add_argument("--private", action="store_true", help="Create the repo as private when used with --create-repo.")
    parser.add_argument("--workers", type=_positive_int, default=4, help="Number of concurrent artifact preparation workers (default: 4).")
    parser.add_argument("--batch-size", type=_positive_int, default=100, help="Artifacts per Hub commit (default: 100).")
    parser.add_argument("--force", action="store_true", help="Upload paths that already exist in the repository.")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be uploaded without committing.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    filter_re = re.compile(args.filter) if args.filter else None
    include_executable = args.include in ("executable", "both")
    include_implementation = args.include in ("implementation", "both")

    executable_ids = _instance_ids(args.source, "executable", filter_re) if include_executable else []
    implementation_ids = _instance_ids(args.source, "implementation", filter_re) if include_implementation else []

    if not executable_ids and not implementation_ids:
        raise SystemExit("no instances selected under source")

    print(f"Selected {len(executable_ids)} executable(s), {len(implementation_ids)} implementation(s).")
    if args.dry_run:
        for iid in executable_ids:
            print(f"DRY-RUN executable/{iid}/executable")
        for iid in implementation_ids:
            print(f"DRY-RUN implementation/{iid}.tar.gz")
        return

    _disable_hf_progress_bars()

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

    remote_files: set[str] = set()
    if not args.force:
        try:
            remote_files = _repo_files(
                repo_id=repo_id,
                repo_type=args.repo_type,
                revision=args.revision,
                token=args.token,
            )
        except Exception as error:
            print(
                "WARNING: could not list existing repository files; uploading all selected artifacts: "
                f"{type(error).__name__}: {error}",
                file=sys.stderr,
            )

    tasks: list[tuple[str, str]] = []
    for iid in executable_ids:
        if f"executable/{iid}/executable" not in remote_files:
            tasks.append(("executable", iid))
    for iid in implementation_ids:
        if f"implementation/{iid}.tar.gz" not in remote_files:
            tasks.append(("implementation", iid))

    selected = len(executable_ids) + len(implementation_ids)
    skipped_existing = selected - len(tasks)
    if skipped_existing:
        print(f"Skipping {skipped_existing} artifact(s) already present in {repo_id}@{args.revision}.")

    committed = 0
    failed = 0
    batch_count = (len(tasks) + args.batch_size - 1) // args.batch_size
    with tempfile.TemporaryDirectory(prefix="programbench-ground-truth-hf-") as tmp:
        tmp_root = Path(tmp)
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            for batch_index, start in enumerate(range(0, len(tasks), args.batch_size), start=1):
                batch_tasks = tasks[start : start + args.batch_size]
                futures: dict[Future[PreparedUpload], tuple[str, str]] = {
                    executor.submit(
                        _prepare_one,
                        kind=kind,
                        instance_id=iid,
                        source=args.source,
                        tmp_root=tmp_root,
                    ): (kind, iid)
                    for kind, iid in batch_tasks
                }
                prepared: list[PreparedUpload] = []
                for future in as_completed(futures):
                    kind, iid = futures[future]
                    try:
                        prepared.append(future.result())
                    except Exception as error:
                        failed += 1
                        _warn_failed(kind, iid, error)

                if not prepared:
                    continue
                try:
                    _commit_batch(
                        uploads=prepared,
                        repo_id=repo_id,
                        repo_type=args.repo_type,
                        revision=args.revision,
                        commit_message=args.commit_message,
                        token=args.token,
                    )
                except Exception as error:
                    failed += len(prepared)
                    print(
                        f"WARNING: skipping batch {batch_index}/{batch_count} "
                        f"({len(prepared)} artifacts) after {type(error).__name__}: {error}",
                        file=sys.stderr,
                    )
                else:
                    committed += len(prepared)
                    batch_size = sum(upload.size for upload in prepared)
                    processed = min(start + len(batch_tasks), len(tasks))
                    print(
                        f"[{processed}/{len(tasks)}] committed batch {batch_index}/{batch_count}: "
                        f"{len(prepared)} artifact(s) ({_format_size(batch_size)})",
                        flush=True,
                    )
                finally:
                    for upload in prepared:
                        if upload.kind == "implementation":
                            upload.local_path.unlink(missing_ok=True)

    print(
        f"Finished: {committed} committed, {skipped_existing} already present, "
        f"{failed} skipped after errors."
    )


if __name__ == "__main__":
    main()
