# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the root directory of
# this source tree.

"""Prune the specification discussion that only dropped reference tests exercised."""

from __future__ import annotations

import argparse
import json
import logging
import re
import shutil
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from programbench.codex import build_codex_shell_command, run_codex_in_container, sum_codex_usage
from programbench.container import ensure_cleanroom_codex_image
from programbench.iteration_polish import write_directory_diff
from programbench.skipped_tests import load_skipped_tests_document
from programbench.test_spec_links import TEST_SPEC_LINKS_FILENAME
from programbench.utils.instance_filters import filter_instances

log = logging.getLogger(__name__)

DROPPED_REASONS = frozenset({"internet_required", "our_gt_broad_mutant_kill", "our_gt_flaky"})
DEFAULT_SOURCE = Path("output/debug_iterative_v43_production/iter_0")
DEFAULT_OUTPUT = Path("output/debug_iterative_v43_production/iter_0_postfix")
DEFAULT_SKIPPED_TESTS = Path("ground_truth/skipped-tests")
DEFAULT_TASKS_FILE = Path("ground_truth/valid_task.txt")
DEFAULT_TESTS_DIR = Path("extracted-tests")
DEFAULT_CODEX_COMMAND = (
    "npx -y @openai/codex@0.158.0 --dangerously-bypass-approvals-and-sandbox "
    "exec --cd /workspace --skip-git-repo-check"
)
DEFAULT_MODEL = "codex/gpt-5.6-luna"
DEFAULT_REASONING = "high"
DEFAULT_TIMEOUT = 3600
SPEC_FILENAME = "spec.md"
SECTION_FILENAME = "section.md"

_SPEC_HEADER = re.compile(r"^##\s+Spec\s+(\d+)\b")


def split_spec_sections(text: str) -> list[tuple[str, str]]:
    """Split a spec into ``(label, chunk)`` blocks that rejoin to the original text.

    A block's label is its ``Spec N`` name, or ``""`` for the preamble and for
    any other ``##`` heading, which still terminates the section before it.
    Fenced blocks are tracked because several specs quote ``##`` lines inside
    sample output.
    """
    blocks: list[tuple[str, list[str]]] = [("", [])]
    fenced = False
    for line in text.splitlines(keepends=True):
        if line.startswith("```"):
            fenced = not fenced
        elif not fenced and line.startswith("## "):
            match = _SPEC_HEADER.match(line)
            blocks.append((f"Spec {int(match.group(1))}" if match else "", []))
        blocks[-1][1].append(line)
    return [(label, "".join(lines)) for label, lines in blocks]


def dropped_test_names(document: dict[str, Any]) -> set[str]:
    return {
        item["name"]
        for item in document["skipped_tests"]
        if DROPPED_REASONS.intersection(reason["id"] for reason in item["reasons"])
    }


def section_tests(
    links: dict[str, Any], *, dropped: set[str], skipped: set[str]
) -> dict[str, dict[str, list[dict[str, str]]]]:
    """Bucket each section's linked tests into the ones scoring drops and the ones it keeps.

    Tests skipped for any other reason are in neither bucket: they no longer
    justify a requirement, but they are not what this pass removes either.
    """
    sections: dict[str, dict[str, list[dict[str, str]]]] = {
        label: {"dropped": [], "retained": []} for label in links["spec_sections"]
    }
    for function in links["test_functions"]:
        if function["id"] in dropped:
            bucket = "dropped"
        elif function["id"] in skipped:
            continue
        else:
            bucket = "retained"
        for label in function["target_specs"]:
            sections[label][bucket].append(
                {"name": function["id"], "description": function["description"]}
            )
    return sections


def postfix_section_prompt(*, task: str, label: str) -> str:
    return f"""\
You are pruning one section of the specification for ProgramBench task `{task}`.

Reference tests were removed from the scored suite. The specification still describes
behavior that only those tests exercised, so it now states requirements nothing checks.
Remove that discussion, and nothing else.

## Workspace

- `{SECTION_FILENAME}`: the complete text of `## {label}`, and the only file you may edit.
- `spec/{SPEC_FILENAME}`: the whole specification, for context. Do not edit it.
- `dropped_tests.json`: the tests linked to `{label}` that were removed from the scored suite.
- `retained_tests.json`: the tests linked to `{label}` that remain in the scored suite and must still pass.
- `test/<branch>/eval/`: the source of every test named in those two files.
- `/workspace/executable`: the reference implementation. Run it when you need to see what a requirement describes.

## Task

Read the body of every test in `dropped_tests.json` and find what it actually asserts:
the exact invocation, the exact expected output, the exact exit status. Then delete from
`{SECTION_FILENAME}` the requirements, examples, literals, and prose that exist only to pin
down those assertions. Leave everything else exactly as it is.

Read the bodies of the tests in `retained_tests.json` the same way before you delete
anything. A retained test can assert the same behavior or need it to reach its own
assertion. In that case, the statement has to stay.

## Rules

- Never remove or weaken anything a test in `retained_tests.json` depends on, as an
  assertion or as a precondition of one. Where a requirement serves both sets, keep it.
- If it is unclear how the deletion will affect other tests, leave it as is.
- The tests are immutable and authoritative, so never edit them.
- A test file holds tests from both sets. Judge each one by the list it appears in, not by
  the file or class it shares with its neighbours.
- A requirement no dropped test touches is out of scope; leave it alone.
- Never renumber sections; `{label}` keeps its number and the other sections keep theirs.
- Deleting a requirement means deleting it, not restating it as optional, unspecified, or
  "may vary". The removed behavior is no longer part of the contract at all.
- If nothing in the section is specific to the dropped tests, leave `{SECTION_FILENAME}` unchanged.

## Output

- Leave the pruned section in `{SECTION_FILENAME}`.
- Reply with one sentence naming what you removed, or `unchanged`.
"""


def _postfix_section(
    *,
    task: str,
    label: str,
    chunk: str,
    tests: dict[str, list[dict[str, str]]],
    workspace: Path,
    image: str,
    spec_dir: Path,
    tests_dir: Path,
    model: str,
    reasoning_effort: str,
    codex_command: str,
    timeout: int,
) -> dict[str, Any]:
    workspace.mkdir(parents=True)
    shutil.copytree(spec_dir, workspace / "spec", symlinks=True)
    # Only `eval/`. Its parent is the upstream checkout, and a spec author who
    # reads the implementation stops writing a black-box specification.
    for branch in sorted({test["name"].partition("/")[0] for test in tests["dropped"] + tests["retained"]}):
        shutil.copytree(tests_dir / branch / "eval", workspace / "test" / branch / "eval", symlinks=True)
    (workspace / SECTION_FILENAME).write_text(chunk)
    (workspace / "dropped_tests.json").write_text(json.dumps(tests["dropped"], indent=2))
    (workspace / "retained_tests.json").write_text(json.dumps(tests["retained"], indent=2))
    started = time.time()
    result = run_codex_in_container(
        build_codex_shell_command(
            codex_command,
            prompt=postfix_section_prompt(task=task, label=label),
            model=model.removeprefix("codex/"),
            reasoning_effort=reasoning_effort,
            diagnostic_action=f"postfix {label} for {task}",
        ),
        cwd=workspace,
        image=image,
        timeout=timeout,
        copy_back_files=[SECTION_FILENAME],
    )
    record = {
        "label": label,
        "dropped_tests": [test["name"] for test in tests["dropped"]],
        "retained_test_count": len(tests["retained"]),
        "returncode": result["returncode"],
        "usage": result.get("usage", {}),
        "usage_calls": result.get("usage_calls", 0),
        "duration_seconds": time.time() - started,
    }
    if result["returncode"] != 0:
        return {**record, "section": chunk, "error": f"Codex exited {result['returncode']}: {str(result.get('stderr', '')).strip()}"}
    # Restore the block's own trailing blank line: dropping the last paragraph
    # otherwise leaves the next `## Spec N` heading glued to this section.
    edited = (workspace / SECTION_FILENAME).read_text().rstrip("\n") + chunk[len(chunk.rstrip("\n")) :]
    header = chunk.splitlines(keepends=True)[0]
    if not edited.startswith(header):
        return {**record, "section": chunk, "error": f"Pruned {label} no longer starts with its heading"}
    return {**record, "section": edited, "changed": edited != chunk}


def postfix_task(
    *,
    task: str,
    source: Path,
    output: Path,
    skipped_tests: Path,
    tests_dir: Path = DEFAULT_TESTS_DIR,
    model: str = DEFAULT_MODEL,
    reasoning_effort: str = DEFAULT_REASONING,
    codex_command: str = DEFAULT_CODEX_COMMAND,
    timeout: int = DEFAULT_TIMEOUT,
    section_workers: int = 4,
    force: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Rewrite one task's spec with every dropped-test-only requirement pruned."""
    spec_in = source / "spec" / task
    spec_out = output / "spec" / task
    links_in = source / "test-spec-links" / task / TEST_SPEC_LINKS_FILENAME
    log_dir = output / "log" / task
    if spec_out.exists() and not force:
        return {"instance_id": task, "status": "skipped", "reason": "spec_out_exists", "spec_out": str(spec_out)}

    document = load_skipped_tests_document(skipped_tests, task=task)
    sections = section_tests(
        json.loads(links_in.read_text()),
        dropped=dropped_test_names(document),
        skipped={item["name"] for item in document["skipped_tests"]},
    )
    blocks = split_spec_sections((spec_in / SPEC_FILENAME).read_text())
    jobs = [
        (index, label)
        for index, (label, _) in enumerate(blocks)
        if label in sections and sections[label]["dropped"]
    ]

    shutil.rmtree(spec_out, ignore_errors=True)
    shutil.copytree(spec_in, spec_out, symlinks=True)
    shutil.rmtree(output / "test-spec-links" / task, ignore_errors=True)
    shutil.copytree(links_in.parent, output / "test-spec-links" / task, symlinks=True)
    log_dir.mkdir(parents=True, exist_ok=True)
    (log_dir / "section_tests.json").write_text(
        json.dumps({label: sections[label] for _, label in jobs}, indent=2, sort_keys=True)
    )

    results: list[dict[str, Any]] = []
    if jobs and not dry_run:
        image = ensure_cleanroom_codex_image(task)
        with tempfile.TemporaryDirectory(prefix="programbench-spec-postfix-") as root_name:
            with ThreadPoolExecutor(max_workers=min(section_workers, len(jobs))) as executor:
                results = list(
                    executor.map(
                        lambda job: _postfix_section(
                            task=task,
                            label=job[1],
                            chunk=blocks[job[0]][1],
                            tests=sections[job[1]],
                            workspace=Path(root_name) / f"section_{job[0]:04d}",
                            image=image,
                            spec_dir=spec_in,
                            tests_dir=tests_dir / task,
                            model=model,
                            reasoning_effort=reasoning_effort,
                            codex_command=codex_command,
                            timeout=timeout,
                        ),
                        jobs,
                    )
                )
        for (index, _), result in zip(jobs, results):
            blocks[index] = (blocks[index][0], result["section"])
        (spec_out / SPEC_FILENAME).write_text("".join(chunk for _, chunk in blocks))

    write_directory_diff(before=spec_in, after=spec_out, output=log_dir / "spec.diff.patch")
    payload = {
        "instance_id": task,
        "status": "failed" if any(result.get("error") for result in results) else "ok",
        "dry_run": dry_run,
        "spec_in": str(spec_in),
        "spec_out": str(spec_out),
        "test_spec_links": str(links_in),
        "sections": [{key: value for key, value in result.items() if key != "section"} for result in results],
        "pending_sections": [
            {
                "label": label,
                "dropped": len(sections[label]["dropped"]),
                "retained": len(sections[label]["retained"]),
            }
            for _, label in jobs
        ] if dry_run else [],
        "changed_sections": [result["label"] for result in results if result.get("changed")],
        "usage": sum_codex_usage([result["usage"] for result in results]),
        "usage_calls": sum(int(result["usage_calls"]) for result in results),
        "spec_diff": str(log_dir / "spec.diff.patch"),
    }
    (log_dir / "postfix_spec.traj.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return payload


def run_postfix_batch(
    *,
    source: Path = DEFAULT_SOURCE,
    output: Path = DEFAULT_OUTPUT,
    skipped_tests: Path = DEFAULT_SKIPPED_TESTS,
    tests_dir: Path = DEFAULT_TESTS_DIR,
    tasks_file: Path | None = DEFAULT_TASKS_FILE,
    filter_spec: str = "",
    slice_spec: str = "",
    workers: int = 1,
    section_workers: int = 4,
    model: str = DEFAULT_MODEL,
    reasoning_effort: str = DEFAULT_REASONING,
    codex_command: str = DEFAULT_CODEX_COMMAND,
    timeout: int = DEFAULT_TIMEOUT,
    force: bool = False,
    dry_run: bool = False,
) -> list[dict[str, Any]]:
    listed = (
        {line.strip() for line in tasks_file.read_text().splitlines() if line.strip()}
        if tasks_file
        else None
    )
    tasks = filter_instances(
        [
            {"instance_id": path.name}
            for path in sorted((source / "spec").iterdir())
            if (listed is None or path.name in listed)
            and (source / "test-spec-links" / path.name / TEST_SPEC_LINKS_FILENAME).is_file()
        ],
        filter_spec=filter_spec,
        slice_spec=slice_spec,
    )
    if listed is not None:
        log.info("Task list %s: %d listed, %d runnable under %s", tasks_file, len(listed), len(tasks), source)
    if not tasks:
        log.warning("No tasks selected under %s", source)
        return []

    log.info("Pruning dropped-test requirements for %d task(s)", len(tasks))
    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(
                postfix_task,
                task=task["instance_id"],
                source=source,
                output=output,
                skipped_tests=skipped_tests,
                tests_dir=tests_dir,
                model=model,
                reasoning_effort=reasoning_effort,
                codex_command=codex_command,
                timeout=timeout,
                section_workers=section_workers,
                force=force,
                dry_run=dry_run,
            ): task["instance_id"]
            for task in tasks
        }
        for future in as_completed(futures):
            try:
                results.append(future.result())
            except Exception as error:
                log.error("Spec postfix failed for %s: %s", futures[future], error, exc_info=True)
                results.append({"instance_id": futures[future], "status": type(error).__name__, "error": str(error)})
    return sorted(results, key=lambda result: result["instance_id"])


def summary_lines(results: list[dict[str, Any]]) -> list[str]:
    """One line per task, plus one per section a dry run would prune."""
    counts: dict[str, int] = {}
    for result in results:
        counts[result["status"]] = counts.get(result["status"], 0) + 1
    lines = ["Spec postfix summary: " + ", ".join(f"{status}={count}" for status, count in sorted(counts.items()))]
    for result in results:
        pending = result.get("pending_sections") or []
        detail = (
            result.get("error")
            or (f"{len(pending)} section(s) to prune" if pending else "")
            or ", ".join(result.get("changed_sections") or [])
            or "no change"
        )
        lines.append(f"  {result['status']}: {result['instance_id']} ({detail})")
        lines.extend(
            f"      {section['label']}: {section['dropped']} dropped, {section['retained']} retained"
            for section in pending
        )
    if any(result.get("pending_sections") for result in results):
        lines.append(
            f"Would prune {sum(len(result['pending_sections']) for result in results)} section(s) across "
            f"{sum(1 for result in results if result['pending_sections'])} task(s)"
        )
    return lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Remove specification discussion that only the dropped reference tests exercised."
    )
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE, help=f"Iteration directory to prune (default: {DEFAULT_SOURCE})")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help=f"Output iteration directory (default: {DEFAULT_OUTPUT})")
    parser.add_argument("--skipped-tests", type=Path, default=DEFAULT_SKIPPED_TESTS, help="Skipped-test JSON file or directory")
    parser.add_argument("--tests-dir", type=Path, default=DEFAULT_TESTS_DIR, help=f"Reference-test root holding <instance_id>/<branch>/eval (default: {DEFAULT_TESTS_DIR})")
    parser.add_argument(
        "--tasks", dest="tasks_file", type=Path, default=DEFAULT_TASKS_FILE,
        help=f"File listing the instance ids to run, one per line (default: {DEFAULT_TASKS_FILE}). Pass '' for every task under --source.",
    )
    parser.add_argument("--filter", dest="filter_spec", default="", help="Filter instance ids by regex")
    parser.add_argument("--slice", dest="slice_spec", default="", help="Slice specification, e.g. '0:5'")
    parser.add_argument("-w", "--workers", type=int, default=1, help="Tasks pruned in parallel")
    parser.add_argument("--section-workers", type=int, default=4, help="Sections pruned in parallel per task")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--reasoning", default=DEFAULT_REASONING)
    parser.add_argument("--codex-command", default=DEFAULT_CODEX_COMMAND)
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="Per-section Codex timeout in seconds")
    parser.add_argument("-f", "--force", action="store_true", help="Overwrite an existing output spec")
    parser.add_argument("--dry-run", action="store_true", help="Copy the spec and report the sections that would be pruned")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    results = run_postfix_batch(
        source=args.source,
        output=args.output,
        skipped_tests=args.skipped_tests,
        tests_dir=args.tests_dir,
        tasks_file=args.tasks_file or None,
        filter_spec=args.filter_spec,
        slice_spec=args.slice_spec,
        workers=args.workers,
        section_workers=args.section_workers,
        model=args.model,
        reasoning_effort=args.reasoning,
        codex_command=args.codex_command,
        timeout=args.timeout,
        force=args.force,
        dry_run=args.dry_run,
    )
    for line in summary_lines(results):
        print(line)
    print(f"Pruned specifications: {args.output / 'spec'}")
    return 1 if any(result["status"] not in {"ok", "skipped"} for result in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
