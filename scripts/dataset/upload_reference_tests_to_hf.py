#!/usr/bin/env python3
"""Upload the extracted reference tests to HuggingFace.

Source layout (as laid out in extracted-tests/ by the construction pipeline or scripts/dataset/fetch_task_inputs.py)::

    <source>/<instance_id>/<branch>/...

Each instance holds complete source trees with many small files, so it is
archived as ``tests/<instance_id>.tar.gz`` to keep the number of uploaded
files manageable. Symlinks, including the absolute and dangling ones some test
fixtures rely on, are stored as links. Evaluation downloads and extracts only
the instances it needs (see
``programbench.utils.reference_test_store.resolve_reference_tests_dir``, used
via ``--reference-tests-dir hf://<repo_id>[@revision]``).
"""

from __future__ import annotations

import argparse
import gzip
import os
import re
import sys
import tarfile
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


DEFAULT_SOURCE = Path("extracted-tests")
DEFAULT_TASKS_FILE = Path("ground_truth/valid_task.txt")


def _reset_tarinfo(info: tarfile.TarInfo) -> tarfile.TarInfo:
    info.uid = 0
    info.gid = 0
    info.uname = ""
    info.gname = ""
    return info


def archive_reference_tests(instance_dir: Path, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as gz:
            with tarfile.open(fileobj=gz, mode="w") as tar:
                tar.add(instance_dir, arcname=".", recursive=True, filter=_reset_tarinfo)
    return dest


def _format_size(num_bytes: int) -> str:
    value = float(num_bytes)
    for unit in ("B", "KiB", "MiB", "GiB"):
        if value < 1024 or unit == "GiB":
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024
    return f"{num_bytes} B"


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return parsed


def select_instances(source: Path, tasks_file: Path | None, filter_re: re.Pattern[str] | None) -> list[str]:
    ids = sorted(path.name for path in source.iterdir() if path.is_dir())
    if tasks_file is not None:
        wanted = {line.split("#", 1)[0].strip() for line in tasks_file.read_text().splitlines()} - {""}
        missing = sorted(wanted - set(ids))
        if missing:
            raise SystemExit(f"{len(missing)} listed task(s) have no tests under {source}: {', '.join(missing)}")
        ids = [iid for iid in ids if iid in wanted]
    if filter_re is not None:
        ids = [iid for iid in ids if filter_re.search(iid)]
    return ids


def _resolve_repo_id(repo_id: str, token: str | None) -> str:
    """Prepend the authenticated user's namespace when repo_id has none."""
    if "/" in repo_id:
        return repo_id
    from huggingface_hub import HfApi

    return f'{HfApi(token=token).whoami()["name"]}/{repo_id}'


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE, help="Extracted reference-test root.")
    parser.add_argument(
        "--tasks-file",
        default=str(DEFAULT_TASKS_FILE),
        help=f"Upload only the instances listed here (default: {DEFAULT_TASKS_FILE}); pass '' for every instance.",
    )
    parser.add_argument("--filter", default="", help="Regex further selecting instance IDs to upload.")
    parser.add_argument("--repo-id", default="eth-sri/tsb-reference_tests", help="HuggingFace dataset repo id.")
    parser.add_argument("--repo-type", default="dataset", help="HuggingFace repo type.")
    parser.add_argument("--revision", default="main", help="Target branch/revision.")
    parser.add_argument("--token", default=os.environ.get("HF_TOKEN"), help="HF token; defaults to HF_TOKEN.")
    parser.add_argument("--commit-message", default="Add reference tests", help="Commit message prefix.")
    parser.add_argument("--create-repo", action="store_true", help="Create the HF repo if it does not already exist.")
    parser.add_argument("--private", action="store_true", help="Create the repo as private when used with --create-repo.")
    parser.add_argument("--workers", type=_positive_int, default=4, help="Concurrent archiving workers (default: 4).")
    # Archives reach hundreds of MiB, so a batch is staged on disk before its commit.
    parser.add_argument("--batch-size", type=_positive_int, default=10, help="Archives per Hub commit (default: 10).")
    parser.add_argument("--tmp-dir", type=Path, default=None, help="Staging directory for archives (default: system temp).")
    parser.add_argument("--force", action="store_true", help="Upload archives that already exist in the repository.")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be uploaded without committing.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    filter_re = re.compile(args.filter) if args.filter else None
    ids = select_instances(args.source, Path(args.tasks_file) if args.tasks_file else None, filter_re)
    if not ids:
        raise SystemExit(f"no instances selected under {args.source}")

    print(f"Selected {len(ids)} instance(s).")
    if args.dry_run:
        for iid in ids:
            print(f"DRY-RUN tests/{iid}.tar.gz")
        return

    from huggingface_hub import CommitOperationAdd, HfApi
    from huggingface_hub.utils import disable_progress_bars

    disable_progress_bars()
    api = HfApi(token=args.token)
    repo_id = _resolve_repo_id(args.repo_id, args.token)
    if args.create_repo:
        api.create_repo(repo_id=repo_id, repo_type=args.repo_type, private=args.private, exist_ok=True)

    pending = ids
    if not args.force:
        remote = set(api.list_repo_files(repo_id=repo_id, repo_type=args.repo_type, revision=args.revision))
        pending = [iid for iid in ids if f"tests/{iid}.tar.gz" not in remote]
        if len(pending) < len(ids):
            print(f"Skipping {len(ids) - len(pending)} archive(s) already present in {repo_id}@{args.revision}.")

    committed = failed = 0
    batch_count = (len(pending) + args.batch_size - 1) // args.batch_size
    with tempfile.TemporaryDirectory(prefix="programbench-reference-tests-hf-", dir=args.tmp_dir) as tmp:
        tmp_root = Path(tmp)
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            for batch_index, start in enumerate(range(0, len(pending), args.batch_size), start=1):
                batch = pending[start : start + args.batch_size]
                futures = {
                    executor.submit(archive_reference_tests, args.source / iid, tmp_root / f"{iid}.tar.gz"): iid
                    for iid in batch
                }
                archives: dict[str, Path] = {}
                for future in as_completed(futures):
                    iid = futures[future]
                    try:
                        archives[iid] = future.result()
                    except Exception as error:
                        failed += 1
                        print(f"WARNING: skipping {iid} after {type(error).__name__}: {error}", file=sys.stderr)
                if not archives:
                    continue
                size = sum(path.stat().st_size for path in archives.values())
                try:
                    api.create_commit(
                        repo_id=repo_id,
                        repo_type=args.repo_type,
                        revision=args.revision,
                        operations=[
                            CommitOperationAdd(path_in_repo=f"tests/{iid}.tar.gz", path_or_fileobj=str(path))
                            for iid, path in sorted(archives.items())
                        ],
                        commit_message=f"{args.commit_message}: {len(archives)} instances",
                    )
                except Exception as error:
                    failed += len(archives)
                    print(
                        f"WARNING: skipping batch {batch_index}/{batch_count} after {type(error).__name__}: {error}",
                        file=sys.stderr,
                    )
                else:
                    committed += len(archives)
                    print(
                        f"[{min(start + len(batch), len(pending))}/{len(pending)}] committed batch "
                        f"{batch_index}/{batch_count}: {len(archives)} archive(s) ({_format_size(size)})",
                        flush=True,
                    )
                finally:
                    for path in archives.values():
                        path.unlink(missing_ok=True)

    print(f"Finished: {committed} committed, {len(ids) - len(pending)} already present, {failed} skipped after errors.")
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
