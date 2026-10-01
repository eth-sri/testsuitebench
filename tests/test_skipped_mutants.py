import json

import pytest

from programbench.skipped_mutants import load_skipped_mutants


def test_load_skipped_mutants(tmp_path):
    task = "example__tool.abc1234"
    (tmp_path / f"{task}.json").write_text(json.dumps({
        "instance_id": task,
        "skipped_mutants": [{"id": "repo_3", "reasons": [{"id": "our_gt_target_not_killed"}]}, {"id": "repo_7", "reasons": []}],
    }))
    assert load_skipped_mutants("", task=task) == set()
    assert load_skipped_mutants(tmp_path, task=task) == {"repo_3", "repo_7"}
    assert load_skipped_mutants(tmp_path / f"{task}.json", task=task) == {"repo_3", "repo_7"}
    with pytest.raises(ValueError, match="not other__tool"):
        load_skipped_mutants(tmp_path / f"{task}.json", task="other__tool.0000000")
    with pytest.raises(FileNotFoundError):
        load_skipped_mutants(tmp_path, task="missing__tool.0000000")
