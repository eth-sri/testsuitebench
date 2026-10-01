#!/usr/bin/env python3
"""Fetch the local inputs benchmark construction reads, skipping those already present.

For each task this fills in::

    extracted-tests/<task>/<branch>/...          from --reference-tests-dir (hf://)
    ground_truth/executable/<task>/executable    from --ground-truth-dir (hf://)
    ground_truth/implementation/<task>/...       from --ground-truth-dir (hf://)
    cleanroom/original/<task>/...                from the programbench/<task>:task_cleanroom image

Evaluation does not need this: it resolves hf:// inputs itself and reads
nothing from cleanroom/.
"""

from __future__ import annotations

import argparse
import shutil
import stat
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from programbench.utils.ground_truth_store import (
    download_implementation_archive,
    extract_implementation,
    resolve_ground_truth_dir,
)
from programbench.utils.reference_test_store import download_reference_tests_archive, extract_reference_tests

PARTS = ("tests", "ground-truth", "cleanroom")


def _has_entries(path: Path) -> bool:
    return path.is_dir() and any(path.iterdir())


def fetch_reference_tests(task: str, source: str, root: Path) -> None:
    if _has_entries(root / task):
        return
    extract_reference_tests(download_reference_tests_archive(source, task), root / task)


def fetch_ground_truth(task: str, source: str, root: Path) -> None:
    executable_dir = root / "executable" / task
    if not (executable_dir / "executable").is_file():
        # The HF cache keeps files read-only and without an execute bit.
        downloaded = resolve_ground_truth_dir(source, task) / task
        executable_dir.parent.mkdir(parents=True, exist_ok=True)
        staging = Path(tempfile.mkdtemp(prefix=f".{task}.", dir=executable_dir.parent))
        shutil.copytree(downloaded, staging / task)
        (staging / task / "executable").chmod(0o755)
        (staging / task).replace(executable_dir)
        staging.rmdir()
    implementation_dir = root / "implementation" / task
    if not _has_entries(implementation_dir):
        extract_implementation(download_implementation_archive(source, task), implementation_dir)


def fetch_cleanroom(task: str, root: Path) -> None:
    target = root / task
    if not _has_entries(target):
        image = f"programbench/{task.replace('__', '_1776_')}:task_cleanroom"
        subprocess.run(["docker", "pull", "--quiet", image], check=True, stdout=subprocess.DEVNULL)
        container = subprocess.run(["docker", "create", image], check=True, capture_output=True, text=True).stdout.strip()
        root.mkdir(parents=True, exist_ok=True)
        staging = Path(tempfile.mkdtemp(prefix=f".{task}.", dir=root))
        try:
            subprocess.run(["docker", "cp", f"{container}:/workspace/.", str(staging / task)], check=True)
        finally:
            subprocess.run(["docker", "rm", container], check=False, capture_output=True)
        (staging / task).replace(target)
        staging.rmdir()
    # Task images may contain execute-only ./executable files; host tar must
    # read them to stream the cleanroom back into containers.
    for path in target.rglob("*"):
        if path.is_file() and not path.is_symlink():
            mode = path.stat().st_mode
            if not mode & stat.S_IRUSR:
                path.chmod(mode | stat.S_IRUSR)


def fetch_task(task: str, args: argparse.Namespace) -> None:
    if "tests" in args.parts:
        fetch_reference_tests(task, args.reference_tests_dir, args.tests_root)
    if "ground-truth" in args.parts:
        fetch_ground_truth(task, args.ground_truth_dir, args.ground_truth_root)
    if "cleanroom" in args.parts:
        fetch_cleanroom(task, args.cleanroom_root)
    print(f"[{task}] ready", flush=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--task", action="append", default=[], help="Task instance ID (repeatable).")
    parser.add_argument(
        "--tasks-file",
        type=Path,
        default=None,
        help="File listing task instance IDs; defaults to ground_truth/valid_task.txt when no --task is given.",
    )
    parser.add_argument("--parts", nargs="+", choices=PARTS, default=list(PARTS), help="Inputs to fetch (default: all).")
    parser.add_argument("--reference-tests-dir", default="hf://eth-sri/tsb-reference_tests", help="hf://REPO_ID[@REVISION] holding tests/<task>.tar.gz.")
    parser.add_argument("--ground-truth-dir", default="hf://eth-sri/tsb-reference_impl", help="hf://REPO_ID[@REVISION] holding the ground truth.")
    parser.add_argument("--tests-root", type=Path, default=Path("extracted-tests"))
    parser.add_argument("--ground-truth-root", type=Path, default=Path("ground_truth"))
    parser.add_argument("--cleanroom-root", type=Path, default=Path("cleanroom/original"))
    parser.add_argument("--jobs", type=int, default=4, help="Tasks fetched concurrently (default: 4).")
    args = parser.parse_args()
    if args.tasks_file is None and not args.task:
        args.tasks_file = Path("ground_truth/valid_task.txt")
    if args.tasks_file is not None:
        args.task += [
            task for line in args.tasks_file.read_text().splitlines() if (task := line.split("#", 1)[0].strip())
        ]
    return args


def main() -> None:
    args = parse_args()
    failed = 0
    with ThreadPoolExecutor(max_workers=args.jobs) as executor:
        futures = {task: executor.submit(fetch_task, task, args) for task in dict.fromkeys(args.task)}
        for task, future in futures.items():
            try:
                future.result()
            except Exception as error:
                failed += 1
                print(f"[{task}] FAILED: {type(error).__name__}: {error}", file=sys.stderr)
    if failed:
        raise SystemExit(f"{failed} task(s) could not be fetched")


if __name__ == "__main__":
    main()
