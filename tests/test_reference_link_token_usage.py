from __future__ import annotations

import json
from pathlib import Path

import programbench.reference_test_linking as reference_test_linking
from scripts.construction.summarize_iterative_tokens import collect_usage


TASK = "org__repo.123"


def _fixture(tmp_path: Path) -> tuple[Path, Path, Path]:
    spec_dir = tmp_path / "spec"
    spec_dir.mkdir()
    (spec_dir / "spec.md").write_text("## Spec 1\nAlpha.\n## Spec 2\nBeta.\n")
    tests_dir = tmp_path / "reference-tests" / TASK
    branches = {
        "branch_a": "tests.test_cli.test_alpha",
        "branch_b": "tests.test_cli.test_beta",
    }
    for branch, name in branches.items():
        branch_dir = tests_dir / branch
        branch_dir.mkdir(parents=True)
        (branch_dir / "test_cli.py").write_text(f"def {name.rsplit('.', 1)[-1]}(): pass\n")
    (tests_dir / "tests.json").write_text(
        json.dumps(
            {"branches": {branch: {"tests": [name]} for branch, name in branches.items()}}
        )
    )
    previous = tmp_path / "previous.json"
    previous.write_text(
        json.dumps(
            {
                "instance_id": TASK,
                "test_functions": [
                    {
                        "id": f"{branch}/{name}",
                        "branch": branch,
                        "name": name,
                        "target_specs": [f"Spec {index}"],
                        "description": "Checks the linked behavior.",
                    }
                    for index, (branch, name) in enumerate(branches.items(), start=1)
                ],
            }
        )
    )
    return spec_dir, tests_dir, previous


def test_linking_persists_aggregate_usage_without_nested_codex(
    tmp_path: Path, monkeypatch
) -> None:
    spec_dir, tests_dir, previous = _fixture(tmp_path)
    trajectory = (
        tmp_path
        / "iter_1"
        / "log"
        / TASK
        / "link_reference_tests.candidate_spec.traj.json"
    )

    def fake_branch(**kwargs):
        index = kwargs["branch_index"]
        return {
            "branch_index": index,
            "branch": kwargs["branch"],
            "function_count": len(kwargs["functions"]),
            "duration_seconds": 0.1,
            "usage": {"input_tokens": 100 * index, "output_tokens": 10 * index},
            "usage_calls": 1,
            "codex": {"usage": {"input_tokens": 9999}, "usage_calls": 1},
            "test_functions": kwargs["functions"],
        }

    monkeypatch.setattr(reference_test_linking, "_link_reference_test_branch", fake_branch)
    result = reference_test_linking.carry_or_link_reference_tests(
        task=TASK,
        spec_dir=spec_dir,
        tests_dir=tests_dir,
        previous_output=previous,
        output=tmp_path / "next.json",
        spec_changed=True,
        model="codex/gpt-5.5",
        reasoning_effort="high",
        codex_command="codex exec",
        timeout=10,
        branch_workers=2,
        trajectory=trajectory,
    )

    payload = json.loads(trajectory.read_text())
    assert result["usage_calls"] == 2
    assert payload["usage_calls"] == 2
    assert payload["usage"]["input_tokens"] == 300
    assert payload["usage"]["output_tokens"] == 30
    assert all("codex" not in branch for branch in payload["branches"])

    totals, calls = collect_usage(tmp_path, {TASK})
    key = (TASK, 1, "link-reference-tests")
    assert calls[key] == 2
    assert totals[key]["total_tokens"] == 330


def test_carried_links_write_zero_usage_trajectory(tmp_path: Path) -> None:
    spec_dir, tests_dir, previous = _fixture(tmp_path)
    trajectory = (
        tmp_path / "iter_1" / "log" / TASK / "link_reference_tests.candidate_spec.traj.json"
    )
    result = reference_test_linking.carry_or_link_reference_tests(
        task=TASK,
        spec_dir=spec_dir,
        tests_dir=tests_dir,
        previous_output=previous,
        output=tmp_path / "next.json",
        spec_changed=False,
        model="codex/gpt-5.5",
        reasoning_effort="high",
        codex_command="codex exec",
        timeout=10,
        branch_workers=2,
        trajectory=trajectory,
    )

    payload = json.loads(trajectory.read_text())
    assert result["status"] == "carried_forward"
    assert payload["info"]["status"] == "carried_forward"
    assert payload["usage"] == {}
    assert payload["usage_calls"] == 0
