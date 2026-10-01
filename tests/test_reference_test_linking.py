import json
from pathlib import Path

import pytest

import programbench.reference_test_linking as reference_test_linking
from programbench.reference_test_linking import carry_or_link_reference_tests


def _write_fixture(tmp_path: Path) -> tuple[str, Path, Path, list[dict[str, object]]]:
    task = "org__repo.123"
    spec_dir = tmp_path / "spec"
    spec_dir.mkdir()
    (spec_dir / "spec.md").write_text("## Spec 1\nAlpha.\n## Spec 2\nBeta.\n")
    tests_dir = tmp_path / "reference-tests"
    task_tests = tests_dir / task
    branches = {
        "branch_a": ["tests.test_cli.test_alpha"],
        "branch_b": ["tests.test_cli.test_beta"],
    }
    for branch, names in branches.items():
        branch_dir = task_tests / branch
        branch_dir.mkdir(parents=True)
        (branch_dir / "test_cli.py").write_text(f"def {names[0].rsplit('.', 1)[-1]}(): pass\n")
    (task_tests / "tests.json").write_text(
        json.dumps({"branches": {branch: {"tests": names} for branch, names in branches.items()}})
    )
    functions = [
        {
            "id": f"{branch}/{names[0]}",
            "branch": branch,
            "name": names[0],
            "target_specs": [f"Spec {index}"],
            "description": f"Checks behavior {index}.",
        }
        for index, (branch, names) in enumerate(branches.items(), start=1)
    ]
    return task, spec_dir, tests_dir, functions


def test_valid_links_are_carried_forward_without_model_work(tmp_path: Path) -> None:
    task, spec_dir, tests_dir, functions = _write_fixture(tmp_path)
    previous = tmp_path / "iter_0" / "test-spec-links" / task / "test_spec_links.json"
    previous.parent.mkdir(parents=True)
    previous.write_text(json.dumps({"instance_id": task, "test_functions": functions}))
    output = tmp_path / "iter_1" / "test-spec-links" / task / "test_spec_links.json"

    def runner(prompt: str, workspace: Path) -> dict[str, object]:
        raise AssertionError(f"unexpected model call: {prompt} in {workspace}")

    result = carry_or_link_reference_tests(
        task=task,
        spec_dir=spec_dir,
        tests_dir=tests_dir,
        previous_output=previous,
        output=output,
        spec_changed=False,
        model="codex/gpt-5.5",
        reasoning_effort="high",
        codex_command="codex exec",
        timeout=10,
        branch_workers=2,
        runner=runner,
    )

    assert result["status"] == "carried_forward"
    assert json.loads(output.read_text())["test_functions"] == functions


def test_changed_spec_remaps_links_after_polish(tmp_path: Path) -> None:
    task, spec_dir, tests_dir, functions = _write_fixture(tmp_path)
    previous = tmp_path / "previous.json"
    previous.write_text(json.dumps({"instance_id": task, "test_functions": functions}))
    output = tmp_path / "next.json"
    calls: list[str] = []

    def runner(prompt: str, workspace: Path) -> dict[str, object]:
        calls.append(prompt)
        manifest = json.loads((workspace / "test_spec_links.json").read_text())
        assert (workspace / "spec" / "spec.md").is_file()
        function = manifest["test_functions"][0]
        target = "Spec 1" if function["branch"] == "branch_a" else "Spec 2"
        function["target_specs"] = [target]
        function["description"] = "Remapped against the finalized spec."
        return manifest

    result = carry_or_link_reference_tests(
        task=task,
        spec_dir=spec_dir,
        tests_dir=tests_dir,
        previous_output=previous,
        output=output,
        spec_changed=True,
        model="codex/gpt-5.5",
        reasoning_effort="high",
        codex_command="codex exec",
        timeout=10,
        branch_workers=2,
        runner=runner,
    )

    manifest = json.loads(output.read_text())
    assert result["status"] == "linked"
    assert len(calls) == 2
    assert [item["target_specs"] for item in manifest["test_functions"]] == [["Spec 1"], ["Spec 2"]]


def test_cli_excludes_prepared_skipped_tests_by_default(
    tmp_path: Path, monkeypatch,
) -> None:
    task, spec_dir, tests_dir, _ = _write_fixture(tmp_path)
    skipped_tests = tmp_path / "ground_truth" / "skipped-tests"
    skipped_tests.mkdir(parents=True)
    (skipped_tests / f"{task}.json").write_text(
        json.dumps(
            {
                "instance_id": task,
                "skipped_tests": [
                    {
                        "name": "branch_a/tests.test_cli.test_alpha",
                        "reasons": [{"id": "gold_fail"}],
                    }
                ],
            }
        )
    )
    captured: dict[str, object] = {}

    def fake_link(**kwargs):
        captured.update(kwargs)
        return {"output": str(kwargs["output"])}

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(reference_test_linking, "link_reference_tests_to_spec", fake_link)

    assert reference_test_linking.main(
        [
            "--task", task,
            "--spec-dir", str(spec_dir),
            "--tests-dir", str(tests_dir),
            "--output", str(tmp_path / "links.json"),
        ]
    ) == 0
    assert captured["skipped_tests"] == {"branch_a/tests.test_cli.test_alpha"}


@pytest.mark.parametrize(
    ("failing_attempts", "branch_a_calls"), [([], 1), ([1], 2), ([1, 2], 3), ([1, 2, 3], 3)],
)
def test_incomplete_manifest_is_retried_before_the_branch_is_failed(
    tmp_path: Path, failing_attempts: list[int], branch_a_calls: int
) -> None:
    task, spec_dir, tests_dir, functions = _write_fixture(tmp_path)
    previous = tmp_path / "previous.json"
    previous.write_text(json.dumps({"instance_id": task, "test_functions": functions}))
    output = tmp_path / "next.json"
    calls: list[str] = []

    def runner(prompt: str, workspace: Path) -> dict[str, object]:
        calls.append(prompt)
        manifest = json.loads((workspace / "test_spec_links.json").read_text())
        function = manifest["test_functions"][0]
        function["description"] = "Remapped against the finalized spec."
        # Reproduces zstd in v38: the linker returns an entry with no target_specs.
        function["target_specs"] = (
            [] if len(calls) in failing_attempts
            else ["Spec 1" if function["branch"] == "branch_a" else "Spec 2"]
        )
        return manifest

    kwargs = dict(
        task=task, spec_dir=spec_dir, tests_dir=tests_dir, previous_output=previous,
        output=output, spec_changed=True, model="codex/gpt-5.5", reasoning_effort="high",
        codex_command="codex exec", timeout=10, branch_workers=1, runner=runner,
    )
    if len(failing_attempts) < reference_test_linking.DEFAULT_LINK_ATTEMPTS:
        assert carry_or_link_reference_tests(**kwargs)["status"] == "linked"
        assert all(item["target_specs"] for item in json.loads(output.read_text())["test_functions"])
    else:
        with pytest.raises(RuntimeError, match=r"after 3 attempt\(s\): Missing target_specs"):
            carry_or_link_reference_tests(**kwargs)
    # branch_b always links on its first attempt, so it contributes exactly one call.
    assert len(calls) == branch_a_calls + 1
