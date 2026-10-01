import os
import re
import subprocess
from pathlib import Path


def test_parallel_mutant_builder_reuses_only_unchanged_successful_builds(tmp_path: Path) -> None:
    repo = tmp_path / "repo_1"
    repo.mkdir()
    counter = tmp_path / "build-count"
    source = repo / "source.txt"
    source.write_text("one\n")
    build = repo / "build.sh"
    build.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        f"count=0; test ! -f {counter} || count=$(cat {counter})\n"
        f"printf '%s\\n' $((count + 1)) > {counter}\n"
        "cp source.txt executable\n"
    )
    build.chmod(0o755)
    helper = Path(__file__).resolve().parents[1] / "scripts" / "construction" / "build_mutant_repos_parallel.sh"

    first = subprocess.run([str(helper), "--jobs", "1", "--cpus", "4", str(tmp_path)], check=True, text=True, capture_output=True)
    second = subprocess.run([str(helper), "--jobs", "1", "--cpus", "4", str(tmp_path)], check=True, text=True, capture_output=True)

    assert "[mutant-build-metrics] elapsed_second=" in first.stdout
    assert "configured_workers=1" in first.stdout
    assert "mean_build_second=" in first.stdout
    assert "[mutant-build-warmup] serial_build=" in first.stdout
    assert "build finished" in first.stdout
    assert (
        "[mutant-build-plan] mutants=1 parallel_builds=1 total_cpus=4 cpus_per_build=4"
        in first.stdout
    )
    assert "[mutant-build-progress] completed=1/1 compiled=1 reused=0 failed=0" in first.stdout
    assert "build reused (inputs unchanged)" in second.stdout
    assert "[mutant-build-progress] completed=1/1 compiled=0 reused=1 failed=0" in second.stdout
    assert re.search(r"outcome=compiled build_duration_second=\d+\.\d cpus_per_build=4", first.stdout)
    assert re.search(r"outcome=reused build_duration_second=\d+\.\d cpus_per_build=4", second.stdout)
    assert counter.read_text() == "1\n"

    source.write_text("two\n")
    third = subprocess.run([str(helper), "--jobs", "1", "--cpus", "4", str(tmp_path)], check=True, text=True, capture_output=True)

    assert "build finished" in third.stdout
    assert "[mutant-build-progress] completed=1/1 compiled=1 reused=0 failed=0" in third.stdout
    assert counter.read_text() == "2\n"
    assert (repo / "executable").read_text() == "two\n"


def test_parallel_mutant_builder_divides_cpu_budget_across_active_builds(
    tmp_path: Path,
) -> None:
    helper = Path(__file__).resolve().parents[1] / "scripts" / "construction" / "build_mutant_repos_parallel.sh"
    observations = tmp_path / "observations"
    for index in (1, 2):
        repo = tmp_path / f"repo_{index}"
        repo.mkdir()
        build = repo / "build.sh"
        build.write_text(
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            f"printf '%s\\n' \"$MAKEFLAGS|$CARGO_BUILD_JOBS|"
            f"$CMAKE_BUILD_PARALLEL_LEVEL|$GOMAXPROCS|$RAYON_NUM_THREADS|$(nproc)\" "
            f"> {observations}.{index}\n"
            "printf 'executable\\n' > executable\n"
        )
        build.chmod(0o755)

    result = subprocess.run(
        [
            str(helper),
            "--jobs",
            "8",
            "--cpus",
            "4",
            str(tmp_path),
        ],
        check=True,
        text=True,
        capture_output=True,
    )

    assert (
        "[mutant-build-plan] mutants=2 parallel_builds=2 total_cpus=4 cpus_per_build=2"
        in result.stdout
    )
    assert (tmp_path / "observations.1").read_text() == "-j2|2|2|2|2|2\n"
    assert (tmp_path / "observations.2").read_text() == "-j2|2|2|2|2|2\n"


def test_parallel_mutant_builder_reports_missing_executable_as_failure(tmp_path: Path) -> None:
    repo = tmp_path / "repo_1"
    repo.mkdir()
    build = repo / "build.sh"
    build.write_text("#!/usr/bin/env bash\nset -euo pipefail\nexit 0\n")
    build.chmod(0o755)
    helper = Path(__file__).resolve().parents[1] / "scripts" / "construction" / "build_mutant_repos_parallel.sh"

    result = subprocess.run(
        [str(helper), "--jobs", "1", "--cpus", "1", str(tmp_path)],
        check=False,
        text=True,
        capture_output=True,
    )

    assert result.returncode != 0
    assert "compiled=0 reused=0 failed=1" in result.stdout
    assert re.search(r"last=repo_1 outcome=failed build_duration_second=\d+\.\d", result.stdout)
    assert "[repo_1] build failed" in result.stderr
    assert not (repo / "executable").exists()
    assert not (repo / ".programbench-build-cache").exists()


def test_parallel_mutant_builder_uses_installed_rustup_toolchain(tmp_path: Path) -> None:
    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir()
    rustup = fake_bin / "rustup"
    rustup.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        "test \"$1 $2\" = \"show active-toolchain\"\n"
        "printf '1.92.0-x86_64-unknown-linux-gnu (active, default)\\n'\n"
    )
    rustup.chmod(0o755)

    repo = tmp_path / "repo_1"
    repo.mkdir()
    build = repo / "build.sh"
    build.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        "printf '%s\\n' \"$RUSTUP_TOOLCHAIN\" > executable\n"
    )
    build.chmod(0o755)
    helper = Path(__file__).resolve().parents[1] / "scripts" / "construction" / "build_mutant_repos_parallel.sh"
    env = os.environ.copy()
    env.pop("PROGRAMBENCH_MUTANT_RUSTUP_TOOLCHAIN", None)
    env.pop("RUSTUP_TOOLCHAIN", None)
    env["PATH"] = f"{fake_bin}:{env['PATH']}"

    result = subprocess.run(
        [str(helper), "--jobs", "1", "--cpus", "1", str(tmp_path)],
        check=True,
        text=True,
        capture_output=True,
        env=env,
    )

    assert "rust_toolchain=1.92.0-x86_64-unknown-linux-gnu" in result.stdout
    assert (repo / "executable").read_text() == "1.92.0-x86_64-unknown-linux-gnu\n"


def test_live_container_repairs_reuse_successful_staged_builds(tmp_path: Path, monkeypatch) -> None:
    import shutil

    from programbench import mutants

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    isolated = tmp_path / "isolated"
    isolated.mkdir()
    build_root = isolated / "mutants"
    monkeypatch.setattr(mutants, "ISOLATED_BUILD_ROOT", str(isolated))
    monkeypatch.setattr(mutants, "_MUTANT_BUILD_ROOT", str(build_root))

    class LocalEnvironment:
        def copy_in(self, source, destination):
            shutil.copyfile(source, destination.replace("/workspace", str(workspace)))

        def execute(self, command, **kwargs):
            result = subprocess.run(
                ["bash", "-c", command.replace("/workspace", str(workspace))],
                text=True, capture_output=True,
            )
            return {
                "returncode": result.returncode,
                "stdout": result.stdout,
                "output": result.stdout + result.stderr,
            }

    for index in (1, 2, 3):
        repo = workspace / f"repo_{index}"
        repo.mkdir()
        (repo / "source.txt").write_text("broken" if index == 2 else "original")
        (repo / "executable").write_text("untrusted precompiled artifact")
        (repo / ".programbench-build-cache").write_text("untrusted cache")
        (repo / "build.sh").write_text(
            "#!/usr/bin/env bash\nset -euo pipefail\n"
            f"echo build >> '{tmp_path / f'count_{index}'}'\n"
            "test \"$(cat source.txt)\" != broken\n"
            "cp source.txt executable\n"
            # Generated outputs and build-time source edits must not prevent reuse.
            "echo generated > generated.txt\n"
            "echo build-time-edit >> source.txt\n"
        )

    def compile_attempt(attempt):
        return mutants._compile_mutant_repositories_in_live_container(
            LocalEnvironment(), instance_id="test", repo_names=["repo_1", "repo_2", "repo_3"],
            build_jobs=2, build_cpus=2, timeout=30, attempt=attempt,
        )

    (workspace / "repo_3" / "removed.txt").write_text("old input")
    first = compile_attempt(0)
    assert first["returncode"] != 0
    assert first["failed_repositories"] == ["repo_2"]
    assert "compiled=2 reused=0 failed=1" in first["log"]

    (workspace / "repo_2" / "source.txt").write_text("fixed")
    # Also edit a previously successful mutant: it must be rebuilt.
    (workspace / "repo_3" / "source.txt").write_text("changed")
    (workspace / "repo_3" / "removed.txt").unlink()
    second = compile_attempt(1)
    assert second["returncode"] == 0, second
    assert not (build_root / "repo_3" / "removed.txt").exists()
    assert "compiled=2 reused=1 failed=0" in second["log"]
    assert (tmp_path / "count_1").read_text().splitlines() == ["build"]
    assert (tmp_path / "count_2").read_text().splitlines() == ["build", "build"]
    assert (tmp_path / "count_3").read_text().splitlines() == ["build", "build"]
    assert (workspace / "repo_1" / "executable").read_text() == "original"
    assert (workspace / "repo_2" / "executable").read_text() == "fixed"
    assert (workspace / "repo_3" / "executable").read_text() == "changed"

    # Copying executables back must not invalidate source fingerprints.
    third = compile_attempt(2)
    assert third["returncode"] == 0, third
    assert "compiled=0 reused=3 failed=0" in third["log"]

    # New sessions still rebuild from sources instead of trusting prior artifacts.
    fresh = compile_attempt(0)
    assert fresh["returncode"] == 0, fresh
    assert "compiled=3 reused=0 failed=0" in fresh["log"]


def test_build_mutant_executables_skips_a_store_whose_payloads_resolve(tmp_path: Path) -> None:
    import json

    from programbench.mutants import build_mutant_executables

    instance = tmp_path / "org__repo.rev"
    (instance / "repo_1").mkdir(parents=True)
    (instance / "repo_1" / "executable").write_bytes(b"binary")
    (instance / "mutants.json").write_text(
        json.dumps(
            {
                "instance_id": "org__repo.rev",
                "mutants": [{"id": "repo_1", "kind": "wrapper", "payload": "repo_1/executable"}],
            }
        )
    )

    # No image is reachable here, so returning at all proves no container ran.
    assert build_mutant_executables(
        instance={"instance_id": "org__repo.rev", "image_name": "programbench/absent"},
        output=tmp_path,
    ) == {
        "instance_id": "org__repo.rev",
        "status": "skipped",
        "reason": "ready",
        "output": str(instance),
    }
