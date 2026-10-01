# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

"""Resolve a local or HuggingFace-hosted mutant store for eval-tests."""

from pathlib import Path

from programbench.mutant_storage import ARTIFACT_DIR, MANIFEST_NAME, SOURCE_ARTIFACT_DIR, SOURCES_MANIFEST

HF_MUTANTS_PREFIX = "hf://"


def resolve_mutants_dir(mutants_dir: str, instance_id: str, *, with_sources: bool = False) -> Path:
    """Return a local directory containing ``<instance_id>/mutants.json``.

    ``mutants_dir`` is either a local path, or ``hf://<repo_id>[@revision]`` to
    download just this instance's mutants from a HuggingFace dataset uploaded
    with ``scripts/dataset/upload_mutant_store_to_hf.py``. Only the manifest and the
    executable artifacts are fetched; pass ``with_sources`` to also fetch the
    sealed source overlay under ``.artifacts/sources``, which attribution needs
    to rebuild mutant trees but eval-tests does not.
    """
    if not mutants_dir.startswith(HF_MUTANTS_PREFIX):
        return Path(mutants_dir)

    from programbench.utils.hf_download import hf_snapshot_download

    repo_id, _, revision = mutants_dir.removeprefix(HF_MUTANTS_PREFIX).partition("@")
    patterns = [f"{instance_id}/{MANIFEST_NAME}", f"{instance_id}/{ARTIFACT_DIR}/**"]
    if with_sources:
        patterns += [f"{instance_id}/{SOURCES_MANIFEST}", f"{instance_id}/{SOURCE_ARTIFACT_DIR}/**"]
    return hf_snapshot_download(
        repo_id, revision=revision or "main", allow_patterns=patterns, what=f"mutants for {instance_id}"
    )
