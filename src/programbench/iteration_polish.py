# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the root directory of
# this source tree.

"""Prepare the next iterative specification using staged fixed-test evidence."""

from __future__ import annotations

import argparse
import json
import logging
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

from programbench.codex import build_codex_shell_command, run_codex_in_container
from programbench.constants import cleanroom_codex_image
from programbench.failure_attribution import is_spec_fault
from programbench.mutant_storage import hardlink_or_copy

log = logging.getLogger(__name__)

DEFAULT_CODEX_COMMAND = (
    "npx -y @openai/codex@0.158.0 --dangerously-bypass-approvals-and-sandbox "
    "exec --cd /workspace --skip-git-repo-check"
)
DEFAULT_MODEL = "codex/gpt-5.6-luna"
DEFAULT_REASONING = "high"
DEFAULT_TASK = "abishekvashok__cmatrix.5c082c6"
DEFAULT_TIMEOUT = 7200
DEFAULT_POLISH_BATCH_SIZE = 50


def spec_polish_prompt(*, task: str, attribution_path: str) -> str:
    return f"""\
You are improving the specification for the next iteration of ProgramBench task `{task}`.

## Workspace

- `spec/{task}/`: the specification you own.
- `{attribution_path}`: your complete batch of specification-failure attribution records.
- `generated-test/{task}/`: the generated test suite the `generated_test` records refer to, when present. Evidence only; never edit it.
- `/workspace/executable`: the reference implementation this specification describes. Run it.

## Task

- Inspect every entry in the attribution batch. Use its rationale, failure evidence, and relevant specification text to correct the implicated missing, ambiguous, misleading, or contradictory requirement in `spec/{task}/`.
- Address every entry; one change may resolve multiple failures. If an earlier edit already resolves an entry, redundant change is not required.
- Ground each correction in the supplied evidence and keep unrelated requirements unchanged.
- Every literal string, exit status, message or ordering you add to the specification must come from running `/workspace/executable` yourself on that invocation. Run it before editing, for every entry, and specify what you observe.

## Record kinds

Every record carries `kind` and `evidence_source`. Read the evidence the right way round:

- `kind: "reference_test"`, `evidence_source: "candidate"`: a fixed reference test that a CANDIDATE implementation failed. Its `candidate_error_log` and much of its `rationale` quote the CANDIDATE's output: the wrong implementation. Nothing quoted there is reference behavior; the test's expectation is. Use it only to learn which invocation and which expectation failed.
- `kind: "generated_test"`, `evidence_source: "reference"`: a test generated from this specification that failed on the REFERENCE executable. Its `reference_error_log` quotes the reference's real output, which is the truth; the test's expectation is what the specification led the author to believe. Reconcile the specification with the observed output, then confirm by running the invocation.
- `kind: "survived_mutant"`, `evidence_source: "mutant"`: a deliberate deviation from the reference that no valid generated test detected. `mutation` names the violated behavior. State that behavior precisely enough that a future test can catch the deviation.

## Rules

- Modify only files under `spec/{task}/`; run commands and write scratch files anywhere else you like.
- Do not resolve an entry by weakening a requirement. Describing a behavior as optional, unspecified, non-contractual, "may vary", or "need not" is permitted only when you have run the reference executable and observed it actually vary; otherwise state the behavior it exhibits, exactly.
- Replace an inaccurate requirement with the observed behavior rather than deleting it or broadening it into a permission.
- Never create or edit an iteration-local test suite; the external fixed reference suite remains authoritative, and the generated suite is evidence only.
- Every staged record has `fault: "spec_underspecification"` or `fault: "spec_contradiction"`; executable, test and other faults were excluded before batching.
- Use every complete record in the attribution batch as failure evidence. You may query, group, or summarize the batch as needed, but do not omit entries.
- Keep unrelated discovery commands scoped to relevant files. Redirect verbose command output to a temporary file when that makes it easier to inspect.

## Output

- Leave all specification changes under `spec/{task}/`.
- Summarize the specification changes briefly.
"""


def _short_text(value: Any, max_chars: int = 300) -> str:
    """Bound text embedded by other iteration-polish reports."""
    text = str(value or "")
    return text if len(text) <= max_chars else text[:max_chars] + "...[truncated]"


def copy_iteration_spec(*, spec_in: Path, spec_out: Path, force: bool) -> None:
    _copy_tree(spec_in, spec_out, force=force, label="spec", copy_function=shutil.copy2)


def _copy_tree(
    source: Path,
    target: Path,
    *,
    force: bool,
    label: str,
    copy_function: Any = hardlink_or_copy,
) -> None:
    if not source.is_dir():
        raise FileNotFoundError(f"{label} input directory does not exist: {source}")
    if target.exists():
        if not force:
            raise FileExistsError(f"{label} output already exists: {target} (use --force to overwrite)")
        shutil.rmtree(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(
        source,
        target,
        symlinks=True,
        ignore=shutil.ignore_patterns("*.profraw", "__pycache__", ".pytest_cache"),
        copy_function=copy_function,
    )


def carry_reference_test_links(*, previous_output: Path, output: Path) -> dict[str, Any]:
    """Carry the initial reference-test links without invoking an agent."""
    if not previous_output.is_file():
        raise FileNotFoundError(f"Previous test/spec links do not exist: {previous_output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(previous_output, output)
    return {
        "status": "carried_forward",
        "output": str(output),
        "previous_output": str(previous_output),
        "branches": [],
        "usage": {},
        "usage_calls": 0,
    }


def run_codex_polish(
    *,
    iter_dir: Path,
    task: str,
    model: str,
    reasoning_effort: str,
    codex_command: str,
    timeout: int,
    prompt: str,
    diagnostic_action: str,
    stage_paths: list[Path],
    copy_back_paths: list[Path],
) -> dict[str, Any]:
    command = build_codex_shell_command(
        codex_command,
        prompt=prompt,
        model=model.removeprefix("codex/"),
        reasoning_effort=reasoning_effort,
        diagnostic_action=diagnostic_action,
    )
    started = time.time()
    result = run_codex_in_container(
        command,
        cwd=iter_dir,
        timeout=timeout,
        image=cleanroom_codex_image(task),
        stage_paths=stage_paths,
        copy_back_dirs=copy_back_paths,
    )
    log.info("Finished Codex session with status %d", result["returncode"])
    return {
        "command": command,
        "image": result["image"],
        "returncode": result["returncode"],
        "usage": result.get("usage", {}),
        "usage_calls": result.get("usage_calls", 0),
        "stdout": result.get("stdout", ""),
        "stderr": result.get("stderr", ""),
        "duration_seconds": time.time() - started,
    }


def spec_fault_records(attribution: Path | None, mutant_attribution: Path | None = None) -> list[dict[str, Any]]:
    """Every spec-fault verdict from both evaluation directions, labelled by what its log quotes.

    Reference-test records quote the candidate (wrong) output; generated-test records quote the
    reference (true) output. Renaming the log field per kind keeps the polisher from reading one
    as the other, which is how candidate strings ended up in the specification before.
    """
    records = [
        {"kind": "reference_test", "evidence_source": "candidate", **{("candidate_error_log" if key == "error_log" else key): value for key, value in failure.items()}}
        for failure in (json.loads(attribution.read_text()).get("failures", []) if attribution else [])
        if is_spec_fault(failure.get("fault", ""))
    ]
    if mutant_attribution is None:
        return records
    report = json.loads(mutant_attribution.read_text())
    records += [
        {"kind": "generated_test", "evidence_source": "reference", **{("reference_error_log" if key == "error_log" else key): value for key, value in failure.items()}}
        for failure in report.get("test_failures", [])
        if is_spec_fault(failure.get("fault", ""))
    ]
    records += [
        {"kind": "survived_mutant", "evidence_source": "mutant", **mutant}
        for mutant in report.get("mutants", [])
        if is_spec_fault(mutant.get("fault", ""))
    ]
    return records


def prepare_polish_jobs(
    *,
    attribution: Path | None,
    task_log_dir: Path,
    task: str,
    batch_size: int = DEFAULT_POLISH_BATCH_SIZE,
    mutant_attribution: Path | None = None,
) -> list[dict[str, str]]:
    """Create lossless, bounded specification-polish batches."""
    if batch_size < 1:
        raise ValueError("batch_size must be at least 1")
    spec_failures = spec_fault_records(attribution, mutant_attribution)
    jobs: list[dict[str, str]] = []
    batches = [spec_failures[start : start + batch_size] for start in range(0, len(spec_failures), batch_size)]
    for index, failures in enumerate(batches, start=1):
        name = f"spec_{index:03d}"
        batch_path = task_log_dir / f"failure_attribution.{name}.json"
        batch_path.write_text(
            json.dumps(
                {
                    "source": str(attribution or ""),
                    "mutant_source": str(mutant_attribution or ""),
                    "batch": {
                        "index": index,
                        "count": len(failures),
                        "total_batches": len(batches),
                        "total_spec_failures": len(spec_failures),
                    },
                    "failures": failures,
                },
                indent=2,
            )
        )
        prompt_path = task_log_dir / f"polish_{name}.prompt.md"
        prompt = spec_polish_prompt(
            task=task,
            attribution_path=str(batch_path.relative_to(task_log_dir.parent.parent)),
        )
        prompt_path.write_text(prompt)
        jobs.append(
            {
                "kind": "spec",
                "name": name,
                "branch": "",
                "attribution": str(batch_path),
                "prompt": str(prompt_path),
            }
        )

    return jobs


def write_polish_log(output_dir: Path, payload: dict[str, Any], *, filename: str = "traj.json") -> Path:
    path = output_dir / filename
    path.write_text(json.dumps(payload, indent=2))
    return path


def write_directory_diff(*, before: Path, after: Path, output: Path) -> Path:
    result = subprocess.run(
        ["git", "diff", "--no-index", str(before), str(after)],
        capture_output=True,
        text=True,
        errors="replace",
        check=False,
    )
    output.write_text(result.stdout)
    if result.returncode not in {0, 1}:
        raise RuntimeError(f"git diff failed for {before} -> {after}: {result.stderr.strip()}")
    return output


_LITERAL = re.compile(r"`([^`\n]{6,})`")
_TEXT_SUFFIXES = {".md", ".py", ".c", ".h", ".rs", ".go", ".js", ".ts", ".sh", ".txt", ".golden", ".json", ".yaml", ".yml", ".toml", ".cfg", ".ini"}


def _corpus(root: Path, *, skip_names: frozenset[str] = frozenset()) -> str:
    if not root.is_dir():
        return ""
    return "\n".join(
        path.read_text(errors="replace")
        for path in sorted(root.rglob("*"))
        if path.is_file() and path.suffix in _TEXT_SUFFIXES and path.name not in skip_names and path.stat().st_size < 4_000_000
    )


_PLACEHOLDER = re.compile(r"<[^<>`]*>|\{[^{}`]*\}|\b(?:PATH|FILE|NAME|VALUE|OPTION|DIR|URL|N)\b")


def _chunks(literal: str) -> list[str]:
    """Verbatim pieces of a literal between spec placeholders, long enough to be distinctive."""
    return [chunk.strip() for chunk in _PLACEHOLDER.split(literal) if len(chunk.strip()) >= 12]


def flag_candidate_derived_literals(
    *, spec_in: Path, spec_out: Path, candidate_dir: Path, reference_dir: Path, candidate_logs: str = ""
) -> dict[str, Any]:
    """Report backtick literals the polish added that match the candidate and nothing in the reference tests.

    The polisher receives the candidate's output inside the failure records and has copied it into the
    specification as if it were reference behavior. A literal whose distinctive pieces occur in the
    candidate's sources or captured output, and in no reference test or golden file, is the signature
    of that mistake. Prose restatements of candidate behavior are outside what this can see.
    """
    before = set(_LITERAL.findall(_corpus(spec_in)))
    added = set(_LITERAL.findall(_corpus(spec_out))) - before
    candidate = _corpus(candidate_dir, skip_names=frozenset({"spec.md"})) + "\n" + candidate_logs
    reference = _corpus(reference_dir)
    flagged = sorted(
        literal
        for literal in added
        if any(chunk in candidate and chunk not in reference for chunk in _chunks(literal))
    )
    return {"added_literals": len(added), "flagged": flagged}


def polish_iteration(
    *,
    iter_root: Path,
    task: str,
    iteration: int,
    tests_dir: Path,
    skipped_tests: Path | None = None,
    model: str = DEFAULT_MODEL,
    reasoning_effort: str = DEFAULT_REASONING,
    codex_command: str = DEFAULT_CODEX_COMMAND,
    timeout: int = DEFAULT_TIMEOUT,
    batch_size: int = DEFAULT_POLISH_BATCH_SIZE,
    link_branch_workers: int = 4,
    force: bool = False,
    dry_run: bool = False,
    link_runner: Any = None,
) -> dict[str, Any]:
    this_iter = iter_root / f"iter_{iteration}"
    next_iter = iter_root / f"iter_{iteration + 1}"
    task_log_dir = next_iter / "log" / task
    spec_in = this_iter / "spec" / task
    spec_out = next_iter / "spec" / task
    links_in = this_iter / "test-spec-links" / task / "test_spec_links.json"
    links_out = next_iter / "test-spec-links" / task / "test_spec_links.json"
    attribution: Path | None = task_log_dir / "failure_attribution.json"
    mutant_attribution: Path | None = task_log_dir / "mutant_attribution.json"
    generated_tests = next_iter / "generated-test" / task

    # A converged direction is not rerun, so either evidence file may be absent; polishing needs at least one.
    if not attribution.is_file():
        attribution = None
    if not mutant_attribution.is_file():
        mutant_attribution = None
    if attribution is None and mutant_attribution is None:
        raise FileNotFoundError(f"Neither failure_attribution.json nor mutant_attribution.json exists in {task_log_dir}")
    copy_iteration_spec(spec_in=spec_in, spec_out=spec_out, force=force)

    task_log_dir.mkdir(parents=True, exist_ok=True)
    jobs = prepare_polish_jobs(
        attribution=attribution,
        task_log_dir=task_log_dir,
        task=task,
        batch_size=batch_size,
        mutant_attribution=mutant_attribution,
    )
    spec_diff_path = task_log_dir / "spec.diff.patch"

    if dry_run:
        write_directory_diff(before=spec_in, after=spec_out, output=spec_diff_path)
        link_result = carry_reference_test_links(
            previous_output=links_in,
            output=links_out,
        )
        payload = {
            "task": task,
            "iteration": iteration,
            "next_iteration": iteration + 1,
            "dry_run": True,
            "spec_in": str(spec_in),
            "spec_out": str(spec_out),
            "failure_attribution": str(attribution or ""),
            "mutant_attribution": str(mutant_attribution or ""),
            "jobs": jobs,
            "spec_diff": str(spec_diff_path),
            "test_spec_links": link_result,
        }
        log_path = write_polish_log(task_log_dir, payload, filename="polish_spec.traj.json")
        payload["log"] = str(log_path)
        return payload

    job_results = []
    for job in jobs:
        owned_path = spec_out
        result = run_codex_polish(
            iter_dir=next_iter,
            task=task,
            model=model,
            reasoning_effort=reasoning_effort,
            codex_command=codex_command,
            timeout=timeout,
            prompt=Path(job["prompt"]).read_text(),
            diagnostic_action=f"polish iterative {job['kind']} for {job['name']}",
            stage_paths=[owned_path, Path(job["attribution"]), *([generated_tests] if generated_tests.is_dir() else [])],
            copy_back_paths=[owned_path],
        )
        job_results.append({**job, "codex": result})

    write_directory_diff(before=spec_in, after=spec_out, output=spec_diff_path)
    flags = flag_candidate_derived_literals(
        spec_in=spec_in,
        spec_out=spec_out,
        candidate_dir=this_iter / "executable" / task / "submission_untar",
        reference_dir=tests_dir / task,
        candidate_logs="\n".join(str(failure.get("error_log", "")) for failure in (json.loads(attribution.read_text())["failures"] if attribution else [])),
    )
    (task_log_dir / "spec.polish_flags.json").write_text(json.dumps(flags, indent=2))
    if flags["flagged"]:
        log.warning("Polish added %d literal(s) found only in the candidate: %s", len(flags["flagged"]), flags["flagged"])
    failed_jobs = [job for job in job_results if job["codex"]["returncode"] != 0]
    if failed_jobs:
        payload = {
            "task": task,
            "iteration": iteration,
            "next_iteration": iteration + 1,
            "dry_run": False,
            "spec_in": str(spec_in),
            "spec_out": str(spec_out),
            "failure_attribution": str(attribution or ""),
            "mutant_attribution": str(mutant_attribution or ""),
            "jobs": job_results,
            "spec_diff": str(spec_diff_path),
        }
        log_path = write_polish_log(task_log_dir, payload, filename="polish_spec.traj.json")
        names = ", ".join(job["name"] for job in failed_jobs)
        raise RuntimeError(f"Codex polish failed for {names}; see {log_path}")

    link_result = carry_reference_test_links(
        previous_output=links_in,
        output=links_out,
    )
    payload = {
        "task": task,
        "iteration": iteration,
        "next_iteration": iteration + 1,
        "dry_run": False,
        "spec_in": str(spec_in),
        "spec_out": str(spec_out),
        "failure_attribution": str(attribution or ""),
        "mutant_attribution": str(mutant_attribution or ""),
        "jobs": job_results,
        "spec_diff": str(spec_diff_path),
        "polish_flags": flags,
        "test_spec_links": link_result,
    }
    log_path = write_polish_log(task_log_dir, payload, filename="polish_spec.traj.json")
    payload["log"] = str(log_path)
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Copy and polish only the iterative ProgramBench specification.")
    parser.add_argument("--task", default=DEFAULT_TASK, help=f"Task instance id (default: {DEFAULT_TASK})")
    parser.add_argument("--iter", type=int, required=True, help="Current iteration number N; writes iter_N+1")
    parser.add_argument("--tests-dir", type=Path, required=True, help="Fixed reference-test root.")
    parser.add_argument("--skipped-tests", type=Path)
    parser.add_argument(
        "--iter-root",
        default="",
        help="Iteration root. Defaults to output/iterative",
    )
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Codex model (default: {DEFAULT_MODEL})")
    parser.add_argument("--reasoning", default=DEFAULT_REASONING, help=f"Reasoning effort (default: {DEFAULT_REASONING})")
    parser.add_argument(
        "--codex-command",
        default=DEFAULT_CODEX_COMMAND,
        help="Codex command prefix. The polish prompt is appended as the final argument.",
    )
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="Codex timeout in seconds")
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_POLISH_BATCH_SIZE,
        help=f"Maximum specification failures per Codex polish job (default: {DEFAULT_POLISH_BATCH_SIZE})",
    )
    parser.add_argument("--link-branch-workers", type=int, default=4, help="Parallel reference-test link workers")
    parser.add_argument("--dry-run", action="store_true", help="Copy the spec and write its polish prompt without calling Codex")
    parser.add_argument("--force", action="store_true", help="Overwrite iter_N+1/spec if present")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    iter_root = Path(args.iter_root or Path("output") / "iterative")
    result = polish_iteration(
        iter_root=iter_root,
        task=args.task,
        iteration=args.iter,
        tests_dir=args.tests_dir,
        skipped_tests=args.skipped_tests,
        model=args.model,
        reasoning_effort=args.reasoning,
        codex_command=args.codex_command,
        timeout=args.timeout,
        batch_size=args.batch_size,
        link_branch_workers=args.link_branch_workers,
        force=args.force,
        dry_run=args.dry_run,
    )
    print(f"Prepared next iteration: {iter_root / f'iter_{args.iter + 1}'}")
    print(f"Spec: {result['spec_out']}")
    print(f"Spec diff: {result['spec_diff']}")
    print(f"Test/spec links: {result['test_spec_links']['output']}")
    print(f"Log: {result['log']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
