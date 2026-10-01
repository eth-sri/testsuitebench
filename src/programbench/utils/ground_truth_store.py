# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

"""Resolve a local or HuggingFace-hosted ground-truth executable store."""

import shutil
import tarfile
import tempfile
from functools import lru_cache
from pathlib import Path
from threading import Lock

from programbench.constants import GROUND_TRUTH_LIB_DIR
from programbench.mutant_storage import file_sha256

HF_GROUND_TRUTH_PREFIX = "hf://"
IMPLEMENTATION_CACHE = Path.home() / ".cache" / "programbench" / "implementation"
_IMPLEMENTATION_LOCK = Lock()


def resolve_ground_truth_dir(ground_truth_dir: str, instance_id: str) -> Path:
    """Return a local directory containing ``<instance_id>/executable``.

    ``ground_truth_dir`` is either a local path (conventionally
    ``ground_truth/executable``), or ``hf://<repo_id>[@revision]`` to
    download just this instance's executable from a HuggingFace dataset
    uploaded with ``scripts/dataset/upload_ground_truth_to_hf.py``.
    """
    if not ground_truth_dir.startswith(HF_GROUND_TRUTH_PREFIX):
        return Path(ground_truth_dir)

    from programbench.utils.hf_download import hf_snapshot_download

    repo_id, _, revision = ground_truth_dir.removeprefix(HF_GROUND_TRUTH_PREFIX).partition("@")
    base = hf_snapshot_download(
        repo_id,
        revision=revision or "main",
        allow_patterns=f"executable/{instance_id}/**",
        what=f"ground-truth executable for {instance_id}",
    )
    return base / "executable"


def resolve_implementation_dir(ground_truth_dir: str, instance_id: str) -> Path:
    """Return the local ground-truth source tree for ``instance_id``.

    ``ground_truth_dir`` is either a local path (conventionally
    ``ground_truth/implementation``), or ``hf://<repo_id>[@revision]`` to
    download ``implementation/<instance_id>.tar.gz`` from a HuggingFace dataset
    uploaded with ``scripts/dataset/upload_ground_truth_to_hf.py``. Mutant sources are
    sealed as an overlay on this tree, so attribution needs it to rebuild them.
    """
    if not ground_truth_dir.startswith(HF_GROUND_TRUTH_PREFIX):
        return Path(ground_truth_dir) / instance_id
    # Classifier batches run in parallel threads and all want the same tree.
    with _IMPLEMENTATION_LOCK:
        return _download_implementation(ground_truth_dir, instance_id)


def download_implementation_archive(ground_truth_dir: str, instance_id: str) -> Path:
    """Download ``implementation/<instance_id>.tar.gz`` from ``hf://<repo_id>[@revision]``."""
    from programbench.utils.hf_download import hf_snapshot_download

    repo_id, _, revision = ground_truth_dir.removeprefix(HF_GROUND_TRUTH_PREFIX).partition("@")
    return hf_snapshot_download(
        repo_id,
        revision=revision or "main",
        allow_patterns=f"implementation/{instance_id}.tar.gz",
        what=f"ground-truth sources for {instance_id}",
    ) / "implementation" / f"{instance_id}.tar.gz"


@lru_cache(maxsize=None)
def _download_implementation(ground_truth_dir: str, instance_id: str) -> Path:
    archive = download_implementation_archive(ground_truth_dir, instance_id)
    # Keyed by archive content, so a moved revision extracts afresh instead of
    # serving a stale tree that would silently rebuild the wrong mutant sources.
    target = IMPLEMENTATION_CACHE / file_sha256(archive) / instance_id
    if not target.is_dir():
        extract_implementation(archive, target)
    return target


def extract_implementation(archive: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{target.name}.", dir=target.parent))
    with tarfile.open(archive) as tar:
        # Not "data": the sources include fixtures with absolute symlinks, which that
        # filter refuses. "tar" still blocks any member that would be written outside
        # the staging directory.
        tar.extractall(staging / target.name, filter="tar")
    # A concurrent run may have finished the same extraction first; its tree is
    # identical (the cache key is the archive digest), so let it stand.
    if target.is_dir():
        shutil.rmtree(staging)
        return
    (staging / target.name).replace(target)
    shutil.rmtree(staging)


def write_ground_truth_submission_archive(executable: Path, output: Path) -> None:
    """Package a ground-truth executable as a <instance_id>/submission.tar.gz payload."""
    if not executable.is_file():
        raise FileNotFoundError(f"Ground-truth executable does not exist: {executable}")
    with tempfile.TemporaryDirectory(prefix="programbench-ground-truth-tree-") as tmp_name:
        root = Path(tmp_name)
        shutil.copy2(executable, root / "executable")
        (root / "executable").chmod((root / "executable").stat().st_mode | 0o111)
        lib_dir = executable.parent / "lib"
        has_lib = lib_dir.is_dir() and any(lib_dir.iterdir())
        compile_sh = root / "compile.sh"
        compile_sh_lines = ["#!/usr/bin/env sh", "chmod +x ./executable"]
        if has_lib:
            # Evaluation only round-trips the bare executable file across
            # per-branch workspace wipes (see Evaluator._stashed_executable in
            # eval.py): a ./lib sibling would be destroyed by the first wipe.
            # Install it at the fixed, never-wiped path the executable's RPATH
            # points to instead (see _BUNDLE_MISSING_LIBRARIES_SHELL).
            compile_sh_lines.append(f"mkdir -p {GROUND_TRUTH_LIB_DIR} && cp -f ./lib/* {GROUND_TRUTH_LIB_DIR}/")
        compile_sh.write_text("\n".join(compile_sh_lines) + "\n")
        compile_sh.chmod(0o755)
        with tarfile.open(output, "w:gz") as archive:
            archive.add(root / "compile.sh", arcname="compile.sh")
            archive.add(root / "executable", arcname="executable")
            if has_lib:
                archive.add(lib_dir, arcname="lib")
