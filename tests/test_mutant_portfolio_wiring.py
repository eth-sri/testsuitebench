from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_portfolio_defaults_are_wired_through_all_pipeline_runners() -> None:
    generation = (ROOT / "scripts" / "construction" / "generate_mutants.sh").read_text()
    initialization = (ROOT / "scripts" / "construction" / "run_init.sh").read_text()
    batch = (ROOT / "scripts" / "construction" / "run_iterative_all.sh").read_text()

    for script in (generation, initialization, batch):
        assert "target_tests_per_spec=6" in script
        assert "final_mutants_per_spec=2" in script

    for script in (initialization, batch):
        assert '--target-tests-per-spec "${target_tests_per_spec}"' in script
        assert '--final-mutants-per-spec "${final_mutants_per_spec}"' in script
