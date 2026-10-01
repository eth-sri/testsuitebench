import subprocess
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).parents[1] / "scripts" / "construction"


def skip_options(convergence: str) -> list[str]:
    """Run the script's own iteration_skip_options so the mapping is tested, not its source text."""
    body = subprocess.run(
        ["sed", "-n", "/^iteration_skip_options()/,/^}/p", str(SCRIPTS / "run_iterative_all.sh")],
        capture_output=True, text=True, check=True,
    ).stdout
    assert body.strip().endswith("}")
    return subprocess.run(
        ["bash", "-c", f'{body}\niteration_skip_options "$1"', "_", convergence],
        capture_output=True, text=True, check=True,
    ).stdout.split()


def test_dynamic_mode_reruns_one_iteration_at_a_time_and_skips_converged_directions() -> None:
    script = (SCRIPTS / "run_iterative_all.sh").read_text()

    assert "uv run python -m programbench.iteration_convergence" in script
    assert 'if [ "${convergence}" = "acc=1 validity_rate=1 mutation_score=1" ]; then' in script
    assert '--max-error "${converge_max_error}"' in script
    assert "converge_max_error=80" in script
    assert """grep -q '"error_stopped": true' "${convergence_json}" && status=error-stopped""" in script
    assert 'case " $1 " in *" acc=1 "*) printf \'%s\\n\' --skip-solve --skip-eval --skip-classify ;; esac' in script
    assert '"${iterate_args[@]}" --start-iter "${iter}" --iterations 1 "${skip_options[@]}"' in script
    assert 'convergence_json="${iter_root}/iter_$((iter + 1))/stages/${task}/convergence.json"' in script
    # Tasks that already converged are not queued again when the batch is extended.
    assert '[ "${completed_iterations}" -lt "${iterations}" ] && ! task_converged "${task}"' in script
    assert '"${iterate_args[@]}" --start-iter "${completed_iterations}" --iterations "${remaining_iterations}"' in script


def test_polish_accepts_either_evidence_direction() -> None:
    script = (SCRIPTS / "iterate_spec.sh").read_text()

    assert 'if [ ! -f "${attribution}" ] && [ ! -f "${mutant_attribution}" ]; then' in script
    assert "Failure attribution is missing" not in script


@pytest.mark.parametrize(
    ("convergence", "expected"),
    [
        ("acc=0 validity_rate=0 mutation_score=0", []),
        ("acc=1 validity_rate=0 mutation_score=0", ["--skip-solve", "--skip-eval", "--skip-classify"]),
        # Each direction of the mutant loop drops its own classification once it converges; the
        # shared generation and evaluation survive until both have.
        ("acc=0 validity_rate=1 mutation_score=0", ["--skip-validity-classify"]),
        ("acc=0 validity_rate=0 mutation_score=1", ["--skip-mutation-score"]),
        ("acc=0 validity_rate=1 mutation_score=1", ["--skip-mutant-loop"]),
        (
            "acc=1 validity_rate=0 mutation_score=1",
            ["--skip-solve", "--skip-eval", "--skip-classify", "--skip-mutation-score"],
        ),
        (
            "acc=1 validity_rate=1 mutation_score=1",
            ["--skip-solve", "--skip-eval", "--skip-classify", "--skip-mutant-loop"],
        ),
    ],
)
def test_converged_directions_skip_only_their_own_phases(convergence: str, expected: list[str]) -> None:
    assert skip_options(convergence) == expected


def test_iterate_spec_forwards_each_classification_direction_separately() -> None:
    script = (SCRIPTS / "iterate_spec.sh").read_text()

    assert "--skip-test-failures" in script and "--skip-survived-mutants" in script
    for flag in ("--skip-validity-classify", "--skip-mutation-score"):
        assert f"        {flag})" in script
    # Both halves are forwarded to one classifier invocation, so neither may gate the other.
    assert """            if [ "${skip_validity_classify}" = true ]; then
                mutant_classify_args+=(--skip-test-failures)
            fi
            if [ "${skip_mutation_score}" = true ]; then
                mutant_classify_args+=(--skip-survived-mutants)
            fi""" in script


def test_skipping_mutation_score_withholds_the_mutants_that_drive_mutant_evaluation() -> None:
    script = (SCRIPTS / "iterate_spec.sh").read_text()

    # eval-tests runs mutants only when it is given a mutant store, so the saving comes from
    # withholding --mutants-dir rather than from any new flag on the evaluator.
    assert """            if [ "${skip_mutation_score}" = false ]; then
                mutant_eval_args+=(--mutants-dir "${mutants_dir}")
            fi""" in script
    assert script.count('--mutants-dir "${mutants_dir}"') == 2  # mutant eval (conditional) and the classifier
    # Ground truth still runs: validity rate is measured on it and mutation score filters its killing tests through it.
    assert '--ground-truth-dir "${ground_truth_dir}"' in script
