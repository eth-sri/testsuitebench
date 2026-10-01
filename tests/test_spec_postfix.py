import json
import shutil
from pathlib import Path

import pytest

from programbench import spec_postfix
from programbench.spec_postfix import (
    dropped_test_names,
    postfix_task,
    run_postfix_batch,
    section_tests,
    split_spec_sections,
    summary_lines,
)

SPEC = """\
# Tool specification

Preamble prose.

## Spec 1

Always exits 0.

## Spec 2

Fetches `https://example.com` and prints the body.

```text
## Spec 2 is quoted inside this fence and must not split anything
```

Trailing line of Spec 2.

## Notes

Not a numbered section.

## Spec 3

Stable behavior.
"""


def _link(name, *specs):
    return {
        "id": f"branch/{name}",
        "branch": "branch",
        "name": name,
        "target_specs": list(specs),
        "description": f"description of {name}",
    }


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    source = tmp_path / "iter_0"
    (source / "spec" / "org__tool.abc").mkdir(parents=True)
    (source / "spec" / "org__tool.abc" / "spec.md").write_text(SPEC)
    for branch, module in (("branch", "test_cli"), ("other", "test_other")):
        (tmp_path / "extracted-tests" / "org__tool.abc" / branch / "eval" / "tests").mkdir(parents=True)
        (tmp_path / "extracted-tests" / "org__tool.abc" / branch / "eval" / "tests" / f"{module}.py").write_text(
            f"def test_body_of_{branch}(): pass\n"
        )
        # The upstream checkout sits beside eval/ and must never reach the agent.
        (tmp_path / "extracted-tests" / "org__tool.abc" / branch / "main.go").write_text("package main\n")
    (source / "test-spec-links" / "org__tool.abc").mkdir(parents=True)
    (source / "test-spec-links" / "org__tool.abc" / "test_spec_links.json").write_text(
        json.dumps({
            "instance_id": "org__tool.abc",
            "spec_sections": ["Spec 1", "Spec 2", "Spec 3"],
            "test_functions": [
                _link("test_fetch", "Spec 2"),
                {**_link("test_exit_code", "Spec 1", "Spec 2"), "id": "other/test_exit_code", "branch": "other"},
                _link("test_dummy", "Spec 3"),
            ],
        })
    )
    (tmp_path / "skipped").mkdir()
    (tmp_path / "skipped" / "org__tool.abc.json").write_text(
        json.dumps({
            "instance_id": "org__tool.abc",
            "skipped_tests": [
                {"name": "branch/test_fetch", "reasons": [{"id": "internet_required"}]},
                {"name": "branch/test_dummy", "reasons": [{"id": "dummy_pass"}]},
            ],
        })
    )
    return tmp_path


@pytest.fixture(autouse=True)
def stub_cleanroom_image(monkeypatch: pytest.MonkeyPatch) -> None:
    """No test here has docker, and postfix_task only passes the image name through."""
    monkeypatch.setattr(
        spec_postfix, "ensure_cleanroom_codex_image", lambda task: f"programbench/{task}:task_cleanroom_codex"
    )


def test_split_spec_sections_is_lossless_and_fence_aware() -> None:
    blocks = split_spec_sections(SPEC)
    assert "".join(chunk for _, chunk in blocks) == SPEC
    assert [label for label, _ in blocks] == ["", "Spec 1", "Spec 2", "", "Spec 3"]
    assert "quoted inside this fence" in dict(blocks)["Spec 2"]
    assert "Trailing line of Spec 2." in dict(blocks)["Spec 2"]


def test_section_tests_buckets_only_scoring_relevant_links() -> None:
    links = {
        "spec_sections": ["Spec 1", "Spec 2", "Spec 3"],
        "test_functions": [
            _link("test_fetch", "Spec 2"),
            _link("test_exit_code", "Spec 1", "Spec 2"),
            _link("test_dummy", "Spec 3"),
        ],
    }
    sections = section_tests(
        links,
        dropped={"branch/test_fetch"},
        skipped={"branch/test_fetch", "branch/test_dummy"},
    )
    assert [test["name"] for test in sections["Spec 2"]["dropped"]] == ["branch/test_fetch"]
    assert [test["name"] for test in sections["Spec 2"]["retained"]] == ["branch/test_exit_code"]
    assert sections["Spec 1"] == {
        "dropped": [],
        "retained": [{"name": "branch/test_exit_code", "description": "description of test_exit_code"}],
    }
    # A test skipped for any other reason justifies nothing and protects nothing.
    assert sections["Spec 3"] == {"dropped": [], "retained": []}


def test_dropped_test_names_matches_any_dropping_reason() -> None:
    assert dropped_test_names({
        "skipped_tests": [
            {"name": "b/flaky", "reasons": [{"id": "dummy_pass"}, {"id": "our_gt_flaky"}]},
            {"name": "b/killed", "reasons": [{"id": "our_gt_broad_mutant_kill"}]},
            {"name": "b/kept", "reasons": [{"id": "gold_fail"}]},
        ]
    }) == {"b/flaky", "b/killed"}


def test_postfix_task_prunes_only_targeted_sections(workspace: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    seen = []

    def fake_run_codex_in_container(command, *, cwd, image, timeout, copy_back_files):
        seen.append({
            "dropped": json.loads((cwd / "dropped_tests.json").read_text()),
            "retained": json.loads((cwd / "retained_tests.json").read_text()),
            "section": (cwd / "section.md").read_text(),
            "spec": (cwd / "spec" / "spec.md").read_text(),
            "staged": sorted(str(path.relative_to(cwd)) for path in cwd.rglob("*") if path.is_file()),
        })
        # Written without the blank line that separated Spec 2 from the next heading.
        (cwd / "section.md").write_text("## Spec 2\n\nTrailing line of Spec 2.\n")
        return {"returncode": 0, "usage": {"total_tokens": 11}, "usage_calls": 1}

    monkeypatch.setattr(spec_postfix, "run_codex_in_container", fake_run_codex_in_container)

    result = postfix_task(
        task="org__tool.abc",
        source=workspace / "iter_0",
        output=workspace / "iter_0_postfix",
        skipped_tests=workspace / "skipped",
        tests_dir=workspace / "extracted-tests",
    )

    assert result["status"] == "ok"
    assert result["changed_sections"] == ["Spec 2"]
    assert result["usage"] == {"total_tokens": 11}
    assert [test["name"] for test in seen[0]["dropped"]] == ["branch/test_fetch"]
    assert [test["name"] for test in seen[0]["retained"]] == ["other/test_exit_code"]
    assert seen[0]["spec"] == SPEC
    assert len(seen) == 1
    # Both linked branches' suites are staged; neither branch's source is.
    assert "test/branch/eval/tests/test_cli.py" in seen[0]["staged"]
    assert "test/other/eval/tests/test_other.py" in seen[0]["staged"]
    assert not [path for path in seen[0]["staged"] if path.endswith("main.go")]

    assert (workspace / "iter_0_postfix" / "spec" / "org__tool.abc" / "spec.md").read_text() == SPEC.replace(
        SPEC[SPEC.index("## Spec 2") : SPEC.index("## Notes")],
        "## Spec 2\n\nTrailing line of Spec 2.\n\n",
    )
    assert (workspace / "iter_0_postfix" / "test-spec-links" / "org__tool.abc" / "test_spec_links.json").is_file()
    assert "Spec 2" in json.loads(
        (workspace / "iter_0_postfix" / "log" / "org__tool.abc" / "section_tests.json").read_text()
    )


def test_postfix_task_keeps_original_section_when_codex_fails(workspace: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        spec_postfix,
        "run_codex_in_container",
        lambda *args, **kwargs: {"returncode": 3, "stderr": "boom", "usage": {}, "usage_calls": 0},
    )

    result = postfix_task(
        task="org__tool.abc",
        source=workspace / "iter_0",
        output=workspace / "iter_0_postfix",
        skipped_tests=workspace / "skipped",
        tests_dir=workspace / "extracted-tests",
    )

    assert result["status"] == "failed"
    assert "Codex exited 3" in result["sections"][0]["error"]
    assert (workspace / "iter_0_postfix" / "spec" / "org__tool.abc" / "spec.md").read_text() == SPEC


def test_postfix_task_rejects_a_section_that_lost_its_heading(workspace: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run_codex_in_container(command, *, cwd, image, timeout, copy_back_files):
        (cwd / "section.md").write_text("## Spec 9\n\nRenumbered.\n")
        return {"returncode": 0, "usage": {}, "usage_calls": 0}

    monkeypatch.setattr(spec_postfix, "run_codex_in_container", fake_run_codex_in_container)

    result = postfix_task(
        task="org__tool.abc",
        source=workspace / "iter_0",
        output=workspace / "iter_0_postfix",
        skipped_tests=workspace / "skipped",
        tests_dir=workspace / "extracted-tests",
    )

    assert result["status"] == "failed"
    assert "no longer starts with its heading" in result["sections"][0]["error"]
    assert (workspace / "iter_0_postfix" / "spec" / "org__tool.abc" / "spec.md").read_text() == SPEC


def test_postfix_task_dry_run_reports_pending_sections_without_running_codex(
    workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        spec_postfix,
        "run_codex_in_container",
        lambda *args, **kwargs: pytest.fail("dry run must not call Codex"),
    )

    result = postfix_task(
        task="org__tool.abc",
        source=workspace / "iter_0",
        output=workspace / "iter_0_postfix",
        skipped_tests=workspace / "skipped",
        tests_dir=workspace / "extracted-tests",
        dry_run=True,
    )

    assert result["pending_sections"] == [{"label": "Spec 2", "dropped": 1, "retained": 1}]
    assert result["changed_sections"] == []
    assert (workspace / "iter_0_postfix" / "spec" / "org__tool.abc" / "spec.md").read_text() == SPEC
    assert summary_lines([result])[1:] == [
        "  ok: org__tool.abc (1 section(s) to prune)",
        "      Spec 2: 1 dropped, 1 retained",
        "Would prune 1 section(s) across 1 task(s)",
    ]


def test_run_postfix_batch_runs_only_the_listed_tasks(workspace: Path) -> None:
    source = workspace / "iter_0"
    for task in ("org__other.def", "org__third.ghi"):
        shutil.copytree(source / "spec" / "org__tool.abc", source / "spec" / task)
        shutil.copytree(source / "test-spec-links" / "org__tool.abc", source / "test-spec-links" / task)
        shutil.copytree(workspace / "extracted-tests" / "org__tool.abc", workspace / "extracted-tests" / task)
        shutil.copy(workspace / "skipped" / "org__tool.abc.json", workspace / "skipped" / f"{task}.json")
    (workspace / "tasks.txt").write_text("org__third.ghi\n\norg__tool.abc\norg__absent.xyz")

    assert [
        result["instance_id"]
        for result in run_postfix_batch(
            source=source,
            output=workspace / "iter_0_postfix",
            skipped_tests=workspace / "skipped",
            tests_dir=workspace / "extracted-tests",
            tasks_file=workspace / "tasks.txt",
            dry_run=True,
        )
    ] == ["org__third.ghi", "org__tool.abc"]

    assert len(
        run_postfix_batch(
            source=source,
            output=workspace / "iter_0_postfix",
            skipped_tests=workspace / "skipped",
            tests_dir=workspace / "extracted-tests",
            tasks_file=None,
            force=True,
            dry_run=True,
        )
    ) == 3
