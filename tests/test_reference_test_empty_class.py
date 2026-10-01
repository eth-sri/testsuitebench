import json
from pathlib import Path

from programbench.skipped_tests import add_skipped_tests, initialize_skipped_tests


def test_adding_skip_keeps_test_source_unchanged(tmp_path: Path) -> None:
    task = "org__repo.123"
    tasks_dir = tmp_path / "tasks"
    metadata = tasks_dir / task / "tests.json"
    metadata.parent.mkdir(parents=True)
    metadata.write_text(json.dumps({
        "branches": {
            "branch_a": {
                "ignored_tests": [{"name": "test_old", "reasons": [{"id": "gold_fail"}]}]
            }
        }
    }))
    tests = tmp_path / "extracted-tests" / task
    tests.mkdir(parents=True)
    source = tests / "test_cli.py"
    source.write_text("class TestSuite:\n    def test_bad(self):\n        assert False\n")
    before = source.read_text()

    output = tmp_path / "skipped-tests"
    initialize_skipped_tests(task=task, output=output, tasks_dir=tasks_dir)
    added = add_skipped_tests(output, task=task, names={"branch_a/test_bad"})

    assert added == ["branch_a/test_bad"]
    assert source.read_text() == before
    document = json.loads((output / f"{task}.json").read_text())
    assert [item["name"] for item in document["skipped_tests"]] == [
        "branch_a/test_bad",
        "branch_a/test_old",
    ]
