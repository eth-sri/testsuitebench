from __future__ import annotations

import pytest

from programbench.failure_attribution import build_candidate_attribution_prompt
from programbench.iteration_polish import spec_polish_prompt
from programbench.mutant_attribution import build_generated_test_failure_prompt, build_mutant_attribution_prompt
from programbench.mutant_kill_validation import mutant_kill_repair_prompt
from programbench.mutants import MUTANT_GENERATION_PROMPT
from programbench.spec_improvement import specification_prompt
from programbench.test_generation import _codex_test_generation_prompt
from scripts.agents.solve_codex import CODEX_GOAL_WITH_TEST, PROMPT_SPEC_ONLY, PROMPT_WITH_EXECUTABLE


PROMPTS = {
    "spec improvement": specification_prompt(),
    "mutant generation": MUTANT_GENERATION_PROMPT,
    "mutant repair": mutant_kill_repair_prompt(
        task="org__repo.123",
        attempt=1,
        affected_ids=["repo_1"],
    ),
    "spec-only solve": PROMPT_SPEC_ONLY,
    "reference-executable solve": PROMPT_WITH_EXECUTABLE,
    "generated-test solve": CODEX_GOAL_WITH_TEST,
    "candidate failure attribution": build_candidate_attribution_prompt(
        failure_count=1,
        branch="branch_a",
    ),
    "spec polish": spec_polish_prompt(
        task="org__repo.123",
        attribution_path="log/org__repo.123/failure_attribution.json",
    ),
    "generated tests (spec-only)": _codex_test_generation_prompt(),
    "generated tests (spec and binary)": _codex_test_generation_prompt(with_executable=True),
    "generated-test failure attribution": build_generated_test_failure_prompt(failure_count=1),
    "mutant attribution": build_mutant_attribution_prompt(mutant_count=1),
}


@pytest.mark.parametrize(("name", "prompt"), PROMPTS.items(), ids=PROMPTS)
def test_iterative_prompts_use_consistent_markdown_sections(name: str, prompt: str) -> None:
    del name
    common_headings = ["## Workspace", "## Task", "## Rules", "## Output"]
    heading_lines = [line for line in prompt.splitlines() if line.startswith("#")]

    assert all(line.startswith("## ") and not line.startswith("### ") for line in heading_lines)
    assert [prompt.index(heading) for heading in common_headings] == sorted(
        prompt.index(heading) for heading in common_headings
    )
    for heading in heading_lines:
        assert f"\n\n{heading}\n\n" in prompt

    assert "\nRules:" not in prompt
    assert "\nRequirements:" not in prompt
    assert "## Important Note" not in prompt
    assert "## Further Note" not in prompt
