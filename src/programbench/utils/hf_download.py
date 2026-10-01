"""HuggingFace downloads with one start and one end log line instead of per-request noise."""

from __future__ import annotations

import logging
import time
from pathlib import Path

log = logging.getLogger(__name__)

# huggingface_hub issues one request per listing page and per file, and httpx logs
# each at INFO. Keep them out of the run logs; hf_snapshot_download reports instead.
for _noisy in ("httpx", "httpcore"):
    logging.getLogger(_noisy).setLevel(logging.WARNING)


def hf_snapshot_download(repo_id: str, *, revision: str, allow_patterns: str | list[str], what: str) -> Path:
    """``snapshot_download`` of a dataset subset, logging when it starts and when it ends."""
    from huggingface_hub import snapshot_download

    log.info("Fetching %s from hf://%s@%s", what, repo_id, revision)
    start = time.monotonic()
    path = Path(snapshot_download(repo_id, repo_type="dataset", revision=revision, allow_patterns=allow_patterns))
    log.info("Fetched %s in %.1fs", what, time.monotonic() - start)
    return path
