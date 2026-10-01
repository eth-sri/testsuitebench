from __future__ import annotations

import importlib.util
from pathlib import Path


def load_generate_tests_claude():
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "agents" / "generate_tests_claude.py"
    spec = importlib.util.spec_from_file_location("generate_tests_claude", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_container_script_hides_executable_and_validates_fresh_junit():
    generate_tests = load_generate_tests_claude()

    script = generate_tests.build_container_script(
        "claude --dangerously-skip-permissions --print --verbose --output-format stream-json",
        "haiku",
        "",
    )

    assert "--exclude=./executable --exclude=executable" in script
    assert "rm -f /workspace/executable" in script
    assert 'if [ -n "$effort" ]' in script
    assert 'cmd+=(--effort "$effort")' in script
    assert "test -x /workspace/eval/run.sh" in script
    assert "rm -f results.xml" in script
    assert "./run.sh" in script
    assert "xml.etree.ElementTree" in script
    assert "not JUnit XML" in script
    assert "JUnit XML contains no testcases" in script
    assert "last 20 lines" not in script
    assert "tail -n 20" not in script
    assert "find . -type l -lname '/*' -delete" in script
    assert "--exclude=.pytest_tmp" in script
    assert "1000000000" in script
    assert "/tmp/tests.tar.gz" in script
    assert "--sparse" not in script
    assert "-C /workspace eval" in script



def test_container_script_with_reference_executable_uses_code_aware_prompt():
    generate_tests = load_generate_tests_claude()

    script = generate_tests.build_container_script("claude --print", "haiku", "", with_executable=True)
    prompt = generate_tests._codex_test_generation_prompt(with_executable=True)

    assert "install -m 755 /tmp/programbench_reference_executable /workspace/executable" in script
    assert "rm -f /workspace/executable" not in script
    assert "reference executable at `/workspace/executable`" in prompt
    assert "Use the reference executable" in prompt


def test_prompt_matches_programbench_spec_only_generation_contract():
    generate_tests = load_generate_tests_claude()

    prompt = generate_tests._codex_test_generation_prompt(with_executable=False)

    assert "Create a comprehensive test suite under `/workspace/eval`" in prompt
    assert "/workspace/eval/run.sh" in prompt
    assert "/workspace/eval/results.xml" in prompt
    assert "mutation testing" in prompt


def test_official_huge_prompt_maps_documented_binary_name_to_executable():
    generate_tests = load_generate_tests_claude()

    default_prompt = generate_tests._codex_test_generation_prompt()
    official_huge_prompt = generate_tests._codex_test_generation_prompt(official_huge=True)

    assert "original binary name" not in default_prompt
    assert "original binary name" in official_huge_prompt
    assert "`ast-grep`" in official_huge_prompt
    assert "`/workspace/executable`" in official_huge_prompt


def test_default_output_is_eval_tests_compatible():
    generate_tests = load_generate_tests_claude()

    assert generate_tests.DEFAULT_OUTPUT == "output/test-suites/claude"
