# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

"""Bound untrusted diagnostic payloads in JUnit XML without changing outcomes."""

from __future__ import annotations

import argparse
import os
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path


_DIAGNOSTIC_TAGS = {"failure", "error", "system-out", "system-err"}


def truncate_utf8(value: str, max_bytes: int) -> str:
    """Retain useful head/tail context while bounding the encoded byte size."""

    if max_bytes < 1:
        raise ValueError("max_bytes must be positive")
    encoded = value.encode("utf-8")
    if len(encoded) <= max_bytes:
        return value

    marker = (
        f"\n... [ProgramBench truncated JUnit diagnostic; original size: "
        f"{len(encoded)} bytes] ...\n"
    ).encode("utf-8")
    if len(marker) >= max_bytes:
        return marker[:max_bytes].decode("utf-8", errors="ignore")

    retained = max_bytes - len(marker)
    head = encoded[: retained // 2].decode("utf-8", errors="ignore")
    tail = encoded[-(retained - retained // 2) :].decode("utf-8", errors="ignore")
    result = head + marker.decode("utf-8") + tail
    while len(result.encode("utf-8")) > max_bytes:
        tail = tail[1:]
        result = head + marker.decode("utf-8") + tail
    return result


def truncate_junit_diagnostics(root: ET.Element, max_bytes: int) -> int:
    """Cap failure/error and captured-stream diagnostics in a parsed JUnit tree."""

    changed = 0
    for element in root.iter():
        local_tag = element.tag.rsplit("}", 1)[-1]
        if local_tag not in _DIAGNOSTIC_TAGS:
            continue
        if element.text is not None:
            truncated = truncate_utf8(element.text, max_bytes)
            if truncated != element.text:
                element.text = truncated
                changed += 1
        if local_tag in {"failure", "error"} and "message" in element.attrib:
            message = element.attrib["message"]
            truncated = truncate_utf8(message, max_bytes)
            if truncated != message:
                element.attrib["message"] = truncated
                changed += 1
    return changed


def truncate_junit_file(path: Path, max_bytes: int) -> int:
    """Atomically rewrite ``path`` with bounded diagnostics."""

    tree = ET.parse(path)
    changed = truncate_junit_diagnostics(tree.getroot(), max_bytes)
    if changed == 0:
        return 0

    fd, temporary_name = tempfile.mkstemp(
        prefix=".programbench-junit-",
        suffix=".xml",
        dir=path.parent,
    )
    os.close(fd)
    temporary_path = Path(temporary_name)
    try:
        tree.write(temporary_path, encoding="utf-8", xml_declaration=True)
        temporary_path.replace(path)
    finally:
        temporary_path.unlink(missing_ok=True)
    return changed


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    parser.add_argument("max_bytes", type=int)
    args = parser.parse_args()
    changed = truncate_junit_file(args.path, args.max_bytes)
    print(f"ProgramBench truncated {changed} oversized JUnit diagnostic field(s)")


if __name__ == "__main__":
    main()
