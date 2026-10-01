from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_reference_linking_runs_only_during_initialization() -> None:
    initialization = (ROOT / "scripts" / "construction" / "run_init.sh").read_text()
    candidate_polish = (ROOT / "src" / "programbench" / "iteration_polish.py").read_text()

    assert (
        '--trajectory "${iter_root}/iter_0/log/${task}/link_reference_tests.initial.traj.json"'
        in initialization
    )
    assert "reference_test_linking" not in candidate_polish
    assert "link_reference_tests.candidate_spec.traj.json" not in candidate_polish
