"""Resolve a local or HuggingFace-hosted reference-test store."""

import shutil
import tarfile
import tempfile
from functools import lru_cache
from pathlib import Path
from threading import Lock

from programbench.mutant_storage import file_sha256

HF_REFERENCE_TESTS_PREFIX = "hf://"
REFERENCE_TESTS_CACHE = Path.home() / ".cache" / "programbench" / "reference-tests"
_DOWNLOAD_LOCK = Lock()


def is_hf_reference_tests(tests_dir: str | Path) -> bool:
    return str(tests_dir).startswith(HF_REFERENCE_TESTS_PREFIX)


def resolve_reference_tests_dir(tests_dir: str | Path, instance_id: str) -> Path:
    """Return a local directory containing ``<instance_id>/<branch>/``.

    ``tests_dir`` is either a local path (conventionally ``extracted-tests``),
    or ``hf://<repo_id>[@revision]`` to download ``tests/<instance_id>.tar.gz``
    from a HuggingFace dataset uploaded with
    ``scripts/dataset/upload_reference_tests_to_hf.py``. The returned root
    differs per instance, so resolve it for each instance separately.
    """
    if not is_hf_reference_tests(tests_dir):
        return Path(tests_dir)
    # Parallel evaluation threads may request the same instance at once.
    with _DOWNLOAD_LOCK:
        return _download_reference_tests(str(tests_dir), instance_id)


def download_reference_tests_archive(tests_dir: str, instance_id: str) -> Path:
    """Download ``tests/<instance_id>.tar.gz`` from ``hf://<repo_id>[@revision]``."""
    from programbench.utils.hf_download import hf_snapshot_download

    repo_id, _, revision = tests_dir.removeprefix(HF_REFERENCE_TESTS_PREFIX).partition("@")
    archive = hf_snapshot_download(
        repo_id,
        revision=revision or "main",
        allow_patterns=f"tests/{instance_id}.tar.gz",
        what=f"reference tests for {instance_id}",
    ) / "tests" / f"{instance_id}.tar.gz"
    if not archive.is_file():
        raise FileNotFoundError(f"{tests_dir} has no reference tests for {instance_id}")
    return archive


@lru_cache(maxsize=None)
def _download_reference_tests(tests_dir: str, instance_id: str) -> Path:
    archive = download_reference_tests_archive(tests_dir, instance_id)
    # Keyed by archive content, so a moved revision extracts afresh instead of
    # serving stale tests.
    root = REFERENCE_TESTS_CACHE / file_sha256(archive)
    if not (root / instance_id).is_dir():
        extract_reference_tests(archive, root / instance_id)
    return root


def extract_reference_tests(archive: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{target.name}.", dir=target.parent))
    with tarfile.open(archive) as tar:
        # Not "data": test fixtures include deliberate absolute and dangling
        # symlinks, which that filter refuses. "tar" still blocks any member
        # that would be written outside the staging directory.
        tar.extractall(staging / target.name, filter="tar")
    try:
        (staging / target.name).replace(target)
    except OSError:
        # Another process finished the same extraction first; its tree is
        # identical (the cache key is the archive digest), so let it stand.
        if not target.is_dir():
            raise
    # Fixtures may contain read-only directories; leftovers are harmless.
    shutil.rmtree(staging, ignore_errors=True)
