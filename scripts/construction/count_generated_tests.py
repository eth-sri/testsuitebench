#!/usr/bin/env python3
"""Count the JUnit testcases recorded in a generated-test archive."""

from __future__ import annotations

import argparse
import tarfile
import xml.etree.ElementTree as ET
from pathlib import Path, PurePosixPath


def count_generated_tests(archive: Path) -> int:
    """Return the number of testcases in the archive's eval/results.xml."""
    with tarfile.open(archive, "r:gz") as generated_tests:
        results_members = [
            member
            for member in generated_tests.getmembers()
            if PurePosixPath(member.name).parts[-2:] == ("eval", "results.xml")
        ]
        if len(results_members) != 1:
            raise ValueError(
                f"expected exactly one eval/results.xml, found {len(results_members)}"
            )
        results_file = generated_tests.extractfile(results_members[0])
        if results_file is None:
            raise ValueError("eval/results.xml is not a regular file")
        root = ET.parse(results_file).getroot()
    return sum(1 for element in root.iter() if element.tag.rsplit("}", 1)[-1] == "testcase")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("archive", type=Path)
    args = parser.parse_args()
    try:
        print(count_generated_tests(args.archive))
    except (OSError, tarfile.TarError, ET.ParseError, ValueError) as error:
        parser.error(f"cannot count generated tests in {args.archive}: {error}")


if __name__ == "__main__":
    main()
