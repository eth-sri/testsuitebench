# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the root directory of
# this source tree.

"""Shared recovery for Codex classifier batches that come back unusable."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

log = logging.getLogger(__name__)

CLASSIFIER_ERROR_SUBREASONS = frozenset(
    {
        "classifier_failed",
        "invalid_classifier_json",
        "invalid_batch_result",
        "invalid_classifier_item",
        "missing_batch_result",
    }
)


class ClassifierBatchUsage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    phase: str
    batch_index: int
    branch: str = ""
    case_count: int
    usage: dict[str, int] = Field(default_factory=dict)


def retry_classifier_batch(
    classify_once: Callable[..., tuple[list[Any], ClassifierBatchUsage | None]],
    **kwargs: Any,
) -> tuple[list[Any], ClassifierBatchUsage | None]:
    """Split malformed batches, preserving successful cases and all attempt costs.

    Children run sequentially inside the original worker slot. A failed singleton
    terminates recovery, bounding the number of calls to at most 2 * N - 1.
    Semantic unknown judgments do not trigger retries.
    """
    attributions, usage = classify_once(**kwargs)
    failed_indices = [
        i for i, item in enumerate(attributions)
        if item.fault == "unknown" and item.subreason in CLASSIFIER_ERROR_SUBREASONS
    ]
    if not failed_indices:
        return attributions, usage

    for i in failed_indices:
        item = attributions[i]
        item.classifier_errors.append({
            "case_count": len(kwargs["batch"]),
            "subreason": item.subreason,
            "rationale": item.rationale,
            "raw_response": item.raw_response,
        })
    if len(kwargs["batch"]) == 1:
        log.warning("Classifier batch %s failed for a single case: %s",
                    kwargs["batch_index"], attributions[0].rationale)
        return attributions, usage

    size = max(1, (len(kwargs["batch"]) + 1) // 2)
    log.warning("Classifier batch %s has %s malformed results; retrying with batch size %s",
                kwargs["batch_index"], len(failed_indices), size)
    for offset in range(0, len(failed_indices), size):
        indices = failed_indices[offset:offset + size]
        child_kwargs = dict(kwargs, batch=[kwargs["batch"][i] for i in indices])
        workspace = kwargs["workspace"]
        if workspace is not None:
            # Siblings of the parent avoid copying earlier work into retries.
            child_kwargs["workspace"] = workspace.with_name(f"{workspace.name}_retry_{offset // size}")
        recovered, child_usage = retry_classifier_batch(classify_once, **child_kwargs)
        for i, item in zip(indices, recovered, strict=True):
            item.classifier_errors = attributions[i].classifier_errors + item.classifier_errors
            attributions[i] = item
        if child_usage is not None:
            if usage is None:
                usage = child_usage.model_copy(deep=True)
                usage.case_count = len(kwargs["batch"])
            else:
                for key, value in child_usage.usage.items():
                    usage.usage[key] = usage.usage.get(key, 0) + value
    return attributions, usage
