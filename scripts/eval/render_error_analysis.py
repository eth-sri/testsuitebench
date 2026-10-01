#!/usr/bin/env python3
"""Render failure-attribution results as a self-contained HTML report."""

from __future__ import annotations

import argparse
import difflib
import html
import json
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SPEC_HEADING = re.compile(r"^## Spec (\d+)(?::.*)?\s*$", re.MULTILINE)
SPEC_REFERENCE = re.compile(r"\bSpecs?\s+(\d+(?:\s*/\s*\d+)*)", re.IGNORECASE)
HUNK_HEADER = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
STOP_WORDS = {
    "about", "after", "also", "been", "candidate", "does", "failed", "failure",
    "from", "into", "iteration", "must", "process", "requires", "should", "specification",
    "test", "that", "their", "these", "this", "when", "which", "with", "without",
}


@dataclass(frozen=True)
class SpecSection:
    number: int
    start_line: int
    end_line: int
    text: str


@dataclass(frozen=True)
class PatchHunk:
    old_start: int
    text: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Write a simple HTML report for attributed failures and mutant outcomes."
    )
    parser.add_argument("output_dir", type=Path, help="Iterative run directory, e.g. output/debug_iterative_v26")
    parser.add_argument("task", help="Task substring or full instance id, e.g. cmatrix")
    parser.add_argument("iteration", type=int, help="Iteration containing the evaluation and attribution")
    parser.add_argument(
        "--fault",
        default="all",
        choices=("executable", "spec", "spec_underspecification", "spec_contradiction", "test", "mutant", "error", "unknown", "all"),
        help="Attribution to include (default: all)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="HTML destination (default: beside failure_attribution.json)",
    )
    parser.add_argument(
        "--attribution",
        type=Path,
        help="Attribution JSON (failure or mutant) (default: discover it under OUTPUT_DIR/iter_ITERATION/log)",
    )
    parser.add_argument(
        "--eval-json",
        type=Path,
        help="Evaluation JSON (default: use attribution metadata, then the iterative layout)",
    )
    parser.add_argument(
        "--spec",
        type=Path,
        help="Optional specification Markdown file; omitted from report if missing (default: iter_ITERATION-1/spec/TASK/spec.md)",
    )
    parser.add_argument(
        "--patch",
        type=Path,
        help="Specification diff patch (default: spec.diff.patch beside the attribution, if present)",
    )
    parser.add_argument(
        "--mutants-dir",
        type=Path,
        help="Mutant repository directory (default: use attribution metadata)",
    )
    parser.add_argument(
        "--reference-dir",
        type=Path,
        help="Reference source repository (default: ground_truth/implementation/TASK)",
    )
    return parser.parse_args()


def find_attribution(output_dir: Path, iteration: int, task: str) -> Path:
    log_dir = output_dir / f"iter_{iteration}" / "log"
    candidates = sorted(log_dir.glob("*/failure_attribution.json"))
    task_lower = task.lower()
    matches = [path for path in candidates if task_lower in path.parent.name.lower()]
    if not matches:
        raise FileNotFoundError(f"No failure_attribution.json matching {task!r} under {log_dir}")
    if len(matches) > 1:
        names = ", ".join(path.parent.name for path in matches)
        raise ValueError(f"Task {task!r} is ambiguous; matching instances: {names}")
    return matches[0]


def find_attributions(output_dir: Path, iteration: int, task: str) -> list[Path]:
    """Find the standard attribution reports for one task."""
    primary = find_attribution(output_dir, iteration, task)
    mutant = primary.with_name("mutant_attribution.json")
    return [primary, mutant] if mutant.is_file() else [primary]


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object in {path}")
    return value


def parse_spec_sections(spec_text: str) -> dict[int, SpecSection]:
    matches = list(SPEC_HEADING.finditer(spec_text))
    sections: dict[int, SpecSection] = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(spec_text)
        start_line = spec_text.count("\n", 0, match.start()) + 1
        end_line = spec_text.count("\n", 0, end) + (0 if end == len(spec_text) else 1)
        number = int(match.group(1))
        sections[number] = SpecSection(number, start_line, end_line, spec_text[match.start():end].rstrip())
    return sections


def referenced_specs(rationale: str) -> list[int]:
    references: list[int] = []
    for match in SPEC_REFERENCE.finditer(rationale):
        for value in re.split(r"\s*/\s*", match.group(1)):
            number = int(value)
            if number not in references:
                references.append(number)
    return references


def infer_spec(rationale: str, sections: dict[int, SpecSection]) -> list[int]:
    """Pick a fallback section when a rationale says only "the specification"."""
    tokens = {
        token.lower()
        for token in re.findall(r"-[A-Za-z?]|[A-Za-z][A-Za-z0-9_-]{3,}", rationale)
        if token.lower() not in STOP_WORDS
    }
    if not tokens:
        return []
    token_pattern = r"-[A-Za-z?]|[A-Za-z][A-Za-z0-9_-]{3,}"
    section_tokens = {
        number: set(re.findall(token_pattern, section.text.lower()))
        for number, section in sections.items()
    }
    document_frequency = {
        token: sum(token in values for values in section_tokens.values())
        for token in tokens
    }
    scored: list[tuple[float, int]] = []
    for number, values in section_tokens.items():
        overlap = tokens & values
        if overlap:
            rarity_score = sum(1 / document_frequency[token] for token in overlap)
            option_bonus = 2 * sum(token.startswith("-") for token in overlap)
            scored.append((rarity_score + option_bonus, number))
    return [max(scored)[1]] if scored else []


def parse_patch_hunks(patch_text: str) -> list[PatchHunk]:
    lines = patch_text.splitlines()
    hunks: list[PatchHunk] = []
    index = 0
    while index < len(lines):
        match = HUNK_HEADER.match(lines[index])
        if not match:
            index += 1
            continue
        start = index
        index += 1
        while index < len(lines) and not lines[index].startswith("@@ "):
            if lines[index].startswith("diff --git "):
                break
            index += 1
        hunks.append(PatchHunk(int(match.group(1)), "\n".join(lines[start:index])))
    return hunks


def hunk_sections(hunks: list[PatchHunk], sections: dict[int, SpecSection]) -> dict[int, list[PatchHunk]]:
    by_section: dict[int, list[PatchHunk]] = {}
    ordered = sorted(sections.values(), key=lambda section: section.start_line)
    for hunk in hunks:
        owner = next(
            (section for section in reversed(ordered) if section.start_line <= hunk.old_start),
            None,
        )
        if owner is not None:
            by_section.setdefault(owner.number, []).append(hunk)
    return by_section


def patch_is_relevant(rationale: str, hunks: list[PatchHunk]) -> bool:
    """Avoid showing unrelated edits in a broad spec section."""
    ignored = STOP_WORDS | {"valid", "value", "values"}

    def words(value: str) -> set[str]:
        return {
            token.lower()
            for token in re.findall(r"[A-Za-z][A-Za-z0-9_-]{3,}", value)
            if token.lower() not in ignored
        }

    changed_lines = "\n".join(
        line[1:]
        for hunk in hunks
        for line in hunk.text.splitlines()
        if line.startswith(("+", "-")) and not line.startswith(("+++", "---"))
    )
    return len(words(rationale) & words(changed_lines)) >= 2


def path_from_metadata(path_value: str, base: Path) -> Path:
    path = Path(path_value)
    if path.is_absolute() or path.exists():
        return path
    candidate = base / path
    return candidate if candidate.exists() else path


IGNORED_DIFF_PARTS = {".gitignore", ".git", ".artifacts", "build", "executable", ".programbench-build-cache"}


def task_scoped_dir(path: Path, instance_id: str) -> Path:
    nested = path / instance_id
    return nested if nested.is_dir() else path


def source_diff(reference_dir: Path | None, mutant_dir: Path | None, mutant_id: str) -> str:
    if reference_dir is None or not reference_dir.is_dir():
        return "Reference source repository is unavailable."
    if mutant_dir is None or not mutant_dir.is_dir():
        return f"Source repository for {mutant_id} is unavailable."

    def source_files(root: Path) -> dict[Path, Path]:
        return {
            path.relative_to(root): path
            for path in root.rglob("*")
            if path.is_file() and not any(part in IGNORED_DIFF_PARTS for part in path.relative_to(root).parts)
        }

    reference_files = source_files(reference_dir)
    mutant_files = source_files(mutant_dir)
    chunks: list[str] = []
    for relative in sorted(reference_files.keys() | mutant_files.keys()):
        reference_path = reference_files.get(relative)
        mutant_path = mutant_files.get(relative)
        try:
            reference_bytes = reference_path.read_bytes() if reference_path else b""
            mutant_bytes = mutant_path.read_bytes() if mutant_path else b""
        except OSError:
            continue
        if reference_bytes == mutant_bytes or max(len(reference_bytes), len(mutant_bytes)) > 1_000_000:
            continue
        try:
            reference_text = reference_bytes.decode("utf-8")
            mutant_text = mutant_bytes.decode("utf-8")
        except UnicodeDecodeError:
            continue
        chunks.extend(difflib.unified_diff(
            reference_text.splitlines(keepends=True),
            mutant_text.splitlines(keepends=True),
            fromfile=f"reference/{relative}",
            tofile=f"{mutant_id}/{relative}",
        ))
    return "".join(chunks) or "No textual source differences found."


def e(value: object) -> str:
    return html.escape(str(value), quote=True)


CLASSIFICATION_LABELS = {
    "executable": "Executable failure classification",
    "test": "Test failure classification",
    "mutant": "Mutant failure classification",
}

SPEC_FAULTS = {"spec_underspecification", "spec_contradiction"}


def render_attribution_summary(failures: list[dict[str, Any]]) -> str:
    rows: list[str] = []
    known_faults = {"executable", "spec", *SPEC_FAULTS, "test", "mutant", "error", "unknown"}
    for classification, label in CLASSIFICATION_LABELS.items():
        counts = Counter(
            str(failure.get("fault", "unknown"))
            for failure in failures
            if failure.get("classification", "executable") == classification
        )
        count_text = (
            ", ".join(
                f'<span class="fault-{tag if tag in known_faults else "unknown"}">{e(tag)}: {count}</span>'
                for tag, count in sorted(counts.items())
            )
            or "none"
        )
        rows.append(f"<li><strong>{label}</strong>: {sum(counts.values())} error(s) attributed — {count_text}</li>")
    return "".join(rows)


def render_report(
    *,
    instance_id: str,
    iteration: int,
    fault: str,
    failures: list[dict[str, Any]],
    eval_results: dict[str, dict[str, Any]],
    sections: dict[int, SpecSection],
    patch_by_section: dict[int, list[PatchHunk]],
    sources: list[Path],
    item_label: str = "failed test function(s)",
) -> str:
    cards: list[str] = []
    for failure in failures:
        name = str(failure.get("name", "(unnamed test)"))
        result = eval_results.get(name, {})
        extra = result.get("extra") if isinstance(result.get("extra"), dict) else {}
        error_text = failure.get("error_log") or extra.get("text") or extra.get("message") or "No error details recorded."
        rationale = str(failure.get("rationale", ""))
        relevant_specs = failure.get("relevant_specs", [])
        reference_text = " ".join(str(value) for value in relevant_specs) if isinstance(relevant_specs, list) else ""
        spec_numbers = referenced_specs(reference_text) or referenced_specs(rationale) or infer_spec(rationale, sections)

        spec_blocks: list[str] = []
        for number in spec_numbers:
            section = sections.get(number)
            if section is None:
                spec_blocks.append(f'<p class="missing">Spec {number} was referenced but not found.</p>')
                continue
            changes = patch_by_section.get(number, [])
            fix_expected = (
                failure.get("fault") == "spec"
                or failure.get("recommended_action") == "polish_spec"
                or patch_is_relevant(rationale, changes)
            )
            change_html = ""
            if changes and fix_expected:
                diffs = "\n\n".join(hunk.text for hunk in changes)
                change_html = (
                    f'<div class="fix"><strong>Updated in iteration {iteration}</strong>'
                    f'<pre class="diff">{e(diffs)}</pre></div>'
                )
            spec_blocks.append(
                f'<details><summary>Spec {number} (lines {section.start_line}–{section.end_line})'
                f'</summary><pre>{e(section.text)}</pre>{change_html}</details>'
            )

        confidence = failure.get("confidence")
        confidence_text = f" · confidence {confidence:.0%}" if isinstance(confidence, (int, float)) else ""
        fault_name = str(failure.get("fault", "unknown"))
        known_faults = {"executable", "spec", *SPEC_FAULTS, "test", "mutant", "error", "unknown"}
        fault_class = fault_name if fault_name in known_faults else "unknown"
        classification = str(failure.get("classification", "executable"))
        known_classifications = {"executable", "test", "mutant"}
        classification_class = classification if classification in known_classifications else "executable"
        detail_label = str(failure.get("detail_label", "Exact error message"))
        spec_html = (
            "".join(spec_blocks)
            if spec_blocks
            else '<p class="missing">No Spec N reference found in the rationale.</p>'
        )
        cards.append(
            f'<article class="card classification-{classification_class}">'
            f"<h2>{e(name)}</h2>"
            f'<div class="meta"><span class="fault-{fault_class}">{e(fault_name)}</span>'
            f" · {e(failure.get('subreason', 'unspecified'))}{confidence_text}</div>"
            "<h3>Agent rationale</h3>"
            f"<p>{e(failure.get('rationale', 'No rationale recorded.'))}</p>"
            f"<h3>{e(detail_label)}</h3>"
            f"<pre>{e(error_text)}</pre>"
            "<h3>Corresponding specification</h3>" + spec_html + "</article>"
        )

    attribution_summary = render_attribution_summary(failures)
    source_items = "".join(f"<li><code>{e(path)}</code></li>" for path in sources)
    title_fault = "all attributed" if fault == "all" else fault
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Error analysis: {e(instance_id)}, iteration {iteration}</title>
<style>
:root {{ color-scheme: light; font-family: system-ui, sans-serif; color: #202124; background: #f6f7f8; }}
body {{ max-width: 1100px; margin: 0 auto; padding: 2rem 1rem 4rem; }}
h1 {{ margin-bottom: .25rem; }} h2 {{ font-size: 1rem; overflow-wrap: anywhere; }} h3 {{ font-size: .9rem; margin-bottom: .35rem; }}
.subtitle, .meta {{ color: #5f6368; }} .summary {{ margin: 1.5rem 0; }}
.attribution-summary {{ padding-left: 1.4rem; }} .attribution-summary li {{ margin: .45rem 0; }}
.attribution-summary span {{ display: inline-block; border-radius: 999px; padding: .08rem .4rem; }}
.card {{ background: white; border: 1px solid #dfe1e5; border-radius: 8px; padding: 1rem 1.25rem; margin: 1rem 0; }}
.card.classification-executable {{ background: #fffdf9; }}
.card.classification-test {{ background: #f9fcff; }}
.card.classification-mutant {{ background: #fdfaff; }}
.meta span {{ display: inline-block; border-radius: 999px; padding: .12rem .5rem; font-weight: 650; }}
.fault-executable {{ background: #fce8e6; color: #a50e0e; }}
.fault-spec, .fault-spec_underspecification, .fault-spec_contradiction {{ background: #fef3c7; color: #92400e; }}
.fault-test {{ background: #e8f0fe; color: #174ea6; }}
.fault-error {{ background: #f3e8fd; color: #7627bb; }}
.fault-unknown {{ background: #eceff1; color: #455a64; }}
.fault-mutant {{ background: #fce8e6; color: #a50e0e; }}
pre {{ background: #f8f9fa; border: 1px solid #e4e6e8; border-radius: 5px; padding: .8rem; overflow: auto; white-space: pre-wrap; overflow-wrap: anywhere; }}
details {{ margin: .65rem 0; }} summary {{ cursor: pointer; font-weight: 650; }}
.fix {{ border-left: 4px solid #188038; padding-left: .8rem; margin-top: .8rem; }}
.diff {{ background: #f2faf4; }} .missing {{ color: #8a4b00; }} code {{ overflow-wrap: anywhere; }}
</style>
</head>
<body>
<h1>Error analysis</h1>
<div class="subtitle">{e(instance_id)} · iteration {iteration} · {e(title_fault)} failures</div>
<div class="summary">
<strong>{len(failures)} {e(item_label)}</strong>
<ul class="attribution-summary">{attribution_summary}</ul>
<details><summary>Input files</summary><ul>{source_items}</ul></details>
</div>
{"".join(cards) if cards else '<p class="missing">No failures matched this attribution filter.</p>'}
</body>
</html>
"""


def normalize_mutant_failures(
    report: dict[str, Any],
    report_path: Path,
    mutants_dir: Path | None,
    reference_dir: Path | None,
) -> list[dict[str, Any]]:
    test_failures = report.get("test_failures", [])
    mutants = report.get("mutants", [])
    if not isinstance(test_failures, list) or not isinstance(mutants, list):
        raise ValueError(f"Expected test_failures and mutants to be lists in {report_path}")

    failures = [{**item, "classification": "test"} for item in test_failures if isinstance(item, dict)]
    for item in mutants:
        if not isinstance(item, dict) or item.get("fault") == "good" or item.get("status") == "killed":
            continue
        normalized = {**item, "classification": "mutant"}
        mutant_id = str(item.get("mutant_id", "(unnamed mutant)"))
        status = str(item.get("status", "unknown"))
        mutant_repo = mutants_dir / mutant_id if mutants_dir is not None else None
        normalized["name"] = f"Mutant {mutant_id} ({status})"
        normalized["error_log"] = source_diff(reference_dir, mutant_repo, mutant_id)
        normalized["detail_label"] = "Reference → mutant diff"
        other_specs = item.get("other_relevant_specs", [])
        if not isinstance(other_specs, list):
            other_specs = []
        normalized["relevant_specs"] = [
            value for value in [item.get("most_relevant_spec"), *other_specs] if isinstance(value, str) and value
        ]
        failures.append(normalized)
    return failures


def generate(
    output_dir: Path,
    task: str,
    iteration: int,
    fault: str,
    destination: Path | None,
    *,
    attribution_path: Path | None = None,
    eval_path: Path | None = None,
    spec_path: Path | None = None,
    patch_path: Path | None = None,
    mutants_dir: Path | None = None,
    reference_dir: Path | None = None,
) -> Path:
    attribution_paths = (
        [attribution_path]
        if attribution_path is not None
        else find_attributions(output_dir, iteration, task)
        if fault == "all"
        else [find_attribution(output_dir, iteration, task)]
    )
    attribution_path = attribution_paths[0]
    if not attribution_path.is_file():
        raise FileNotFoundError(f"Attribution report does not exist: {attribution_path}")
    attributions = [load_json(path) for path in attribution_paths]
    attribution = attributions[0]
    instance_id = attribution_path.parent.name

    if mutants_dir is None:
        mutants_value = next(
            (report.get("mutants_dir") for report in attributions if isinstance(report.get("mutants_dir"), str)),
            None,
        )
        if isinstance(mutants_value, str):
            mutants_dir = path_from_metadata(mutants_value, Path.cwd())
    if mutants_dir is not None:
        mutants_dir = task_scoped_dir(mutants_dir, instance_id)

    if reference_dir is None:
        reference_candidates = [
            Path("ground_truth/implementation") / instance_id,
            Path("cleanroom/original") / instance_id,
        ]
        reference_dir = next(
            (candidate for candidate in reference_candidates if candidate.is_dir()),
            reference_candidates[0],
        )
    else:
        reference_dir = task_scoped_dir(reference_dir, instance_id)

    if eval_path is None:
        eval_candidates: list[Path] = []
        eval_value = attribution.get("eval_json")
        if isinstance(eval_value, str):
            eval_candidates.append(path_from_metadata(eval_value, Path.cwd()))
        eval_candidates.extend([
            attribution_path.parent / f"{instance_id}.test_eval.json",
            attribution_path.parent / f"{instance_id}.eval.json",
            output_dir / f"iter_{iteration}" / "executable" / instance_id / f"{instance_id}.eval.json",
        ])
        eval_path = next(
            (candidate for candidate in eval_candidates if candidate.is_file()),
            eval_candidates[0],
        )
    if spec_path is None:
        spec_path = output_dir / f"iter_{iteration - 1}" / "spec" / instance_id / "spec.md"
    if patch_path is None:
        patch_path = attribution_path.parent / "spec.diff.patch"

    if not eval_path.is_file():
        raise FileNotFoundError(f"Evaluation JSON does not exist: {eval_path}")

    evaluation = load_json(eval_path)
    is_mutant_report = "test_failures" in attribution or "mutants" in attribution
    item_label = "failed test function(s)"

    if is_mutant_report:
        eval_results: dict[str, dict[str, Any]] = {}
        failures = normalize_mutant_failures(attribution, attribution_path, mutants_dir, reference_dir)
        item_label = "generated-test failure(s) and mutant outcome(s)"
    else:
        results = evaluation.get("test_results", [])
        if not isinstance(results, list):
            raise ValueError(f"Expected test_results to be a list in {eval_path}")
        eval_results = {
            str(result.get("name")): result
            for result in results
            if isinstance(result, dict) and result.get("name")
        }
        failures_value = attribution.get("failures", [])
        if not isinstance(failures_value, list):
            raise ValueError(f"Expected failures to be a list in {attribution_path}")
        failures = [{**item, "classification": "executable"} for item in failures_value if isinstance(item, dict)]

    for report, report_path in zip(attributions[1:], attribution_paths[1:]):
        failures.extend(normalize_mutant_failures(report, report_path, mutants_dir, reference_dir))
        item_label = "executable failure(s), generated-test failure(s), and mutant outcome(s)"

    failures = [
        item
        for item in failures
        if fault == "all"
        or item.get("fault") == fault
        or (fault == "spec" and item.get("fault") in SPEC_FAULTS)
    ]

    # Official-documentation runs do not provide a generated spec.md.
    has_spec = spec_path.is_file()
    spec_text = spec_path.read_text(encoding="utf-8") if has_spec else ""
    sections = parse_spec_sections(spec_text)
    patch_text = patch_path.read_text(encoding="utf-8") if patch_path.exists() else ""
    patch_by_section = hunk_sections(parse_patch_hunks(patch_text), sections)
    sources = [*attribution_paths, eval_path]
    if has_spec:
        sources.append(spec_path)
    if patch_path.exists():
        sources.append(patch_path)

    report = render_report(
        instance_id=instance_id,
        iteration=iteration,
        fault=fault,
        failures=failures,
        eval_results=eval_results,
        sections=sections,
        patch_by_section=patch_by_section,
        sources=sources,
        item_label=item_label,
    )
    destination = destination or attribution_path.parent / f"error_analysis_{fault}.html"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(report, encoding="utf-8")
    return destination


def main() -> None:
    args = parse_args()
    destination = generate(
        args.output_dir,
        args.task,
        args.iteration,
        args.fault,
        args.output,
        attribution_path=args.attribution,
        eval_path=args.eval_json,
        spec_path=args.spec,
        patch_path=args.patch,
        mutants_dir=args.mutants_dir,
        reference_dir=args.reference_dir,
    )
    print(destination)


if __name__ == "__main__":
    main()
