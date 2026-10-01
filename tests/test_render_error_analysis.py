import json

from scripts.eval.render_error_analysis import generate, parse_spec_sections, referenced_specs


def test_referenced_specs_supports_slash_notation() -> None:
    assert referenced_specs("Spec 1/6 and Spec 4 apply; Spec 1 is repeated") == [1, 6, 4]


def test_parse_spec_sections_accepts_heading_titles() -> None:
    sections = parse_spec_sections(
        "# Example\n\n## Spec 13: model inspection\n\nInspect models.\n\n"
        "## Spec 14: autotune validation and final training\n\nTune models.\n"
    )

    assert list(sections) == [13, 14]
    assert sections[14].text.startswith("## Spec 14: autotune validation and final training")


def test_generate_joins_failures_and_marks_spec_fix(tmp_path) -> None:
    root = tmp_path / "run"
    instance = "owner__cmatrix.abc1234"
    log_dir = root / "iter_5" / "log" / instance
    eval_dir = root / "iter_5" / "executable" / instance
    spec_dir = root / "iter_4" / "spec" / instance
    for path in (log_dir, eval_dir, spec_dir):
        path.mkdir(parents=True)

    eval_path = eval_dir / f"{instance}.eval.json"
    eval_path.write_text(json.dumps({"test_results": [{
        "name": "tests.test_color",
        "status": "failure",
        "extra": {"message": "short message", "text": "def test_color():\n    assert <bad>"},
    }]}))
    (spec_dir / "spec.md").write_text("# Example\n\n## Spec 4\n\nColors are flexible.\n\n## Spec 5\n\nOther text.\n")
    (log_dir / "spec.diff.patch").write_text(
        "@@ -3,3 +3,3 @@\n ## Spec 4\n \n-Colors are flexible.\n+Colors are strict.\n"
    )
    (log_dir / "failure_attribution.json").write_text(json.dumps({
        "eval_json": str(eval_path),
        "failures": [{
            "name": "tests.test_color",
            "fault": "spec_contradiction",
            "subreason": "wrong color rule",
            "confidence": 0.9,
            "rationale": "Spec 4 contradicts this test.",
            "recommended_action": "polish_spec",
        }],
    }))

    destination = generate(root, "cmatrix", 5, "spec", None)
    report = destination.read_text()

    assert "def test_color():\n    assert &lt;bad&gt;" in report
    assert "short message" not in report
    assert 'class="fault-spec_contradiction"' in report
    assert "Spec 4 (lines" in report
    assert "Updated in iteration 5" in report
    assert "-Colors are flexible." in report
    assert destination == log_dir / "error_analysis_spec.html"

    standalone_dir = tmp_path / "standalone" / instance
    standalone_dir.mkdir(parents=True)
    standalone_attribution = standalone_dir / "failure_attribution.json"
    standalone_attribution.write_text((log_dir / "failure_attribution.json").read_text())
    standalone_destination = generate(
        tmp_path / "unused",
        instance,
        5,
        "all",
        None,
        attribution_path=standalone_attribution,
        eval_path=eval_path,
        spec_path=spec_dir / "spec.md",
    )
    assert standalone_destination == standalone_dir / "error_analysis_all.html"

    (log_dir / "mutant_attribution.json").write_text(
        json.dumps(
            {
                "test_failures": [
                    {
                        "name": "tests.test_generated",
                        "fault": "test",
                        "rationale": "Spec 4 requires green output.",
                        "error_log": "generated test failed",
                    }
                ],
                "mutants": [
                    {
                        "mutant_id": "repo_3",
                        "status": "survived",
                        "fault": "mutant",
                        "rationale": "Spec 4 is implemented by an equivalent mutant.",
                        "most_relevant_spec": "Spec 4",
                    }
                ],
            }
        )
    )
    combined = generate(root, "cmatrix", 5, "all", None).read_text()
    assert 'class="card classification-executable"' in combined
    assert 'class="card classification-test"' in combined
    assert 'class="card classification-mutant"' in combined
    assert "Executable failure classification</strong>: 1 error(s) attributed" in combined
    assert "Test failure classification</strong>: 1 error(s) attributed" in combined
    assert "Mutant failure classification</strong>: 1 error(s) attributed" in combined
    assert "spec_contradiction: 1" in combined
    assert "test: 1" in combined
    assert "mutant: 1" in combined
    assert "mutant_attribution.json" in combined


def test_generate_renders_mutant_attribution(tmp_path) -> None:
    task = "owner__cmatrix.abc1234"
    report_dir = tmp_path / task
    report_dir.mkdir()
    eval_path = report_dir / f"{task}.test_eval.json"
    eval_path.write_text("{}")
    spec_path = tmp_path / "spec.md"
    spec_path.write_text("# Example\n\n## Spec 4\n\nOutput is green.\n")
    reference_dir = tmp_path / "reference"
    reference_dir.mkdir()
    (reference_dir / "source.c").write_text("return GREEN;\n")
    mutants_dir = tmp_path / "mutants"
    mutant_repo = mutants_dir / "repo_1"
    mutant_repo.mkdir(parents=True)
    (mutant_repo / "source.c").write_text("return RED;\n")
    (mutant_repo / ".gitignore").write_text("build/\n")
    attribution_path = report_dir / "mutant_attribution.json"
    attribution_path.write_text(json.dumps({
        "eval_json": str(report_dir / "old-location" / eval_path.name),
        "test_failures": [{
            "name": "tests.test_color",
            "fault": "test",
            "rationale": "Spec 4 requires green output.",
            "error_log": "expected green",
            "relevant_specs": ["Spec 4"],
        }],
        "mutants": [{
            "mutant_id": "repo_1",
            "status": "survived",
            "fault": "test",
            "rationale": "The generated tests miss Spec 4.",
            "most_relevant_spec": "Spec 4",
            "other_relevant_specs": [],
        }, {
            "mutant_id": "repo_2",
            "status": "killed",
            "fault": "good",
            "rationale": "Killed by the generated tests.",
            "most_relevant_spec": "Spec 4",
            "other_relevant_specs": [],
        }],
    }))

    destination = generate(
        tmp_path,
        task,
        5,
        "all",
        None,
        attribution_path=attribution_path,
        spec_path=spec_path,
        mutants_dir=mutants_dir,
        reference_dir=reference_dir,
    )

    rendered = destination.read_text()
    assert "expected green" in rendered
    assert "Mutant repo_1 (survived)" in rendered
    assert "Reference → mutant diff" in rendered
    assert "--- reference/source.c" in rendered
    assert "+++ repo_1/source.c" in rendered
    assert "-return GREEN;" in rendered
    assert "+return RED;" in rendered
    assert ".gitignore" not in rendered
    assert rendered.count("Exact error message") == 1
    assert "Mutant repo_2" not in rendered
    assert "2 generated-test failure(s) and mutant outcome(s)" in rendered
    assert "Test failure classification</strong>: 1 error(s) attributed" in rendered
    assert "Mutant failure classification</strong>: 1 error(s) attributed" in rendered


def test_generate_without_specification(tmp_path) -> None:
    task = "ast-grep__ast-grep.dde0fe0"
    report_dir = tmp_path / task
    report_dir.mkdir()
    eval_path = report_dir / f"{task}.eval.json"
    eval_path.write_text(json.dumps({"test_results": [{
        "name": "tests.test_match",
        "status": "failure",
        "extra": {"text": "expected a match"},
    }]}))
    attribution_path = report_dir / "failure_attribution.json"
    attribution_path.write_text(json.dumps({
        "eval_json": str(eval_path),
        "failures": [{
            "name": "tests.test_match",
            "fault": "executable",
            "rationale": "The implementation misses a documented match.",
        }],
    }))
    missing_spec = tmp_path / "cleanroom" / "official-huge" / task / "spec.md"

    for spec_path in (missing_spec, None):
        destination = generate(
            tmp_path, task, 1, "all", None,
            attribution_path=attribution_path,
            spec_path=spec_path,
        )
        rendered = destination.read_text()
        assert "expected a match" in rendered
        assert "The implementation misses a documented match." in rendered
        assert str(missing_spec) not in rendered
        assert "spec.md" not in rendered
