"""Create immutable, content-addressed input snapshots for iteration stages."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Sequence

from programbench.mutant_storage import hardlink_or_copy


MANIFEST_DIR = "manifests"


def _update_digest(digest: Any, value: str | bytes) -> None:
    if isinstance(value, str):
        value = value.encode()
    digest.update(len(value).to_bytes(8, "big"))
    digest.update(value)


def directory_digest(path: Path) -> str:
    """Return a stable digest of file contents, paths, and symlink targets."""

    digest = hashlib.sha256()
    for item in sorted(path.rglob("*"), key=lambda candidate: candidate.as_posix()):
        relative = item.relative_to(path).as_posix()
        if item.is_symlink():
            _update_digest(digest, "symlink")
            _update_digest(digest, relative)
            _update_digest(digest, os.readlink(item))
        elif item.is_dir():
            _update_digest(digest, "directory")
            _update_digest(digest, relative)
        elif item.is_file():
            _update_digest(digest, "file")
            _update_digest(digest, relative)
            _update_digest(digest, str(item.stat().st_size))
            with item.open("rb") as source:
                while chunk := source.read(1024 * 1024):
                    digest.update(chunk)
        else:
            raise ValueError(f"Unsupported iteration input: {item}")
    return digest.hexdigest()


def _manifest_for_sources(
    *, stage_dir: Path, task: str, sources: dict[str, Path]
) -> dict[str, object]:
    inputs: dict[str, object] = {}
    for name, source_root in sorted(sources.items()):
        source_task = source_root / task
        if not source_task.is_dir():
            raise FileNotFoundError(f"Iteration input is missing: {source_task}")
        inputs[name] = {
            "source": str(source_root),
            "snapshot": str(stage_dir / name),
            "task": task,
            "sha256": directory_digest(source_task),
        }
    return {"schema_version": 1, "task": task, "inputs": inputs}


def snapshot_iteration_inputs(
    *,
    stage_dir: Path,
    task: str,
    sources: dict[str, Path],
    force: bool = False,
) -> Path:
    """Snapshot task inputs for a stage and return its manifest path.

    An existing snapshot is reused only when its manifest exactly matches the
    current sources. This prevents a resumed run from silently associating an
    old evaluation with changed inputs.
    """

    if not sources:
        raise ValueError("At least one iteration input is required")
    expected = _manifest_for_sources(stage_dir=stage_dir, task=task, sources=sources)
    manifest_path = stage_dir / MANIFEST_DIR / f"{task}.json"
    if manifest_path.exists() and not force:
        try:
            actual = json.loads(manifest_path.read_text())
        except json.JSONDecodeError as exc:
            raise FileExistsError(
                f"Stage snapshot has an invalid manifest: {manifest_path}; "
                "rerun with --force"
            ) from exc
        if actual != expected:
            raise FileExistsError(
                f"Stage inputs changed after the snapshot was created: {manifest_path}; "
                "rerun with --force"
            )
        return manifest_path

    stage_dir.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(
        tempfile.mkdtemp(prefix=f".{stage_dir.name}.", dir=stage_dir.parent)
    )
    try:
        for name, source_root in sources.items():
            destination_root = temporary / name
            destination_root.mkdir(parents=True)
            shutil.copytree(
                source_root / task,
                destination_root / task,
                symlinks=True,
                copy_function=hardlink_or_copy,
            )
        stage_dir.mkdir(parents=True, exist_ok=True)
        for name in sources:
            destination_task = stage_dir / name / task
            destination_task.parent.mkdir(parents=True, exist_ok=True)
            if destination_task.exists() or destination_task.is_symlink():
                if destination_task.is_dir() and not destination_task.is_symlink():
                    shutil.rmtree(destination_task)
                else:
                    destination_task.unlink()
            (temporary / name / task).replace(destination_task)

        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_manifest = temporary / f"{task}.json"
        temporary_manifest.write_text(
            json.dumps(expected, indent=2, sort_keys=True) + "\n"
        )
        temporary_manifest.replace(manifest_path)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)
    return manifest_path


def _parse_inputs(values: Sequence[Sequence[str]]) -> dict[str, Path]:
    sources: dict[str, Path] = {}
    for name, path in values:
        if name in sources:
            raise ValueError(f"Duplicate iteration input name: {name}")
        sources[name] = Path(path)
    return sources


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Create an immutable, hashed snapshot of iteration-stage inputs."
    )
    parser.add_argument("--stage-dir", type=Path, required=True)
    parser.add_argument("--task", required=True)
    parser.add_argument(
        "--input",
        nargs=2,
        action="append",
        default=[],
        metavar=("NAME", "ROOT"),
        help="Snapshot ROOT/<task> as <stage-dir>/NAME/<task>.",
    )
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)
    snapshot_iteration_inputs(
        stage_dir=args.stage_dir,
        task=args.task,
        sources=_parse_inputs(args.input),
        force=args.force,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
