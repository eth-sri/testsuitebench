import io
import tarfile
from pathlib import Path

import pytest

from scripts.construction.count_generated_tests import count_generated_tests


def _write_archive(path: Path, results_xml: bytes, name: str = "eval/results.xml") -> None:
    with tarfile.open(path, "w:gz") as archive:
        info = tarfile.TarInfo(name)
        info.size = len(results_xml)
        archive.addfile(info, io.BytesIO(results_xml))


def test_count_generated_tests_counts_nested_and_namespaced_testcases(tmp_path: Path) -> None:
    archive = tmp_path / "tests.tar.gz"
    _write_archive(
        archive,
        b'<testsuites xmlns="urn:junit"><testsuite><testcase/><testcase/></testsuite></testsuites>',
    )

    assert count_generated_tests(archive) == 2


def test_count_generated_tests_accepts_dot_prefixed_eval_path(tmp_path: Path) -> None:
    archive = tmp_path / "tests.tar.gz"
    _write_archive(archive, b"<testsuite><testcase/></testsuite>", "./eval/results.xml")

    assert count_generated_tests(archive) == 1


def test_count_generated_tests_rejects_missing_results(tmp_path: Path) -> None:
    archive = tmp_path / "tests.tar.gz"
    with tarfile.open(archive, "w:gz"):
        pass

    with pytest.raises(ValueError, match="exactly one"):
        count_generated_tests(archive)
