import shutil
import subprocess
from pathlib import Path

import pytest

from programbench import mutants

# The kernel rejects a single argv element above 32 pages; docker passes the whole
# shell command as one argument, so this is the ceiling the build command must respect.
MAX_ARG_STRLEN = 128 * 1024


class FakeEnv:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.commands: list[str] = []

    def copy_in(self, local_path: Path, container_path: str) -> None:
        target = self.root / container_path.lstrip("/")
        target.parent.mkdir(parents=True, exist_ok=True)
        if local_path.is_dir():
            shutil.copytree(local_path, target, dirs_exist_ok=True)
        else:
            shutil.copy2(local_path, target)

    def execute(self, command: str, **kwargs: object) -> dict[str, object]:
        self.commands.append(command)
        return {"returncode": 0, "stdout": "", "output": ""}


def _build_command(tmp_path: Path, repo_count: int, attempt: int = 0) -> tuple[FakeEnv, str]:
    env = FakeEnv(tmp_path)
    mutants._compile_mutant_repositories_in_live_container(
        env, instance_id="org__repo.123",
        repo_names=[f"repo_{index}" for index in range(1, repo_count + 1)],
        build_jobs=1, build_cpus=1, timeout=60, attempt=attempt,
    )
    return env, env.commands[0]


def _localize(command: str, tmp_path: Path, workspace: Path, build_root: Path) -> str:
    return (
        command.replace("/workspace", str(workspace))
        .replace(mutants._MUTANT_BUILD_ROOT, str(build_root))
        .replace(mutants.ISOLATED_BUILD_ROOT, str(tmp_path / mutants.ISOLATED_BUILD_ROOT.lstrip("/")))
    )


@pytest.mark.parametrize("repo_count", [1, 150, 500, 5000])
def test_build_command_length_is_independent_of_mutant_count(
    tmp_path: Path, repo_count: int
) -> None:
    _, command = _build_command(tmp_path, repo_count)
    baseline = len(_build_command(tmp_path / "baseline", 1)[1])
    assert len(command) == baseline
    assert len(command) < MAX_ARG_STRLEN


def test_build_command_stages_hashes_and_copies_back_every_repo(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    for index in range(1, 4):
        repo = workspace / f"repo_{index}"
        repo.mkdir(parents=True)
        (repo / "source.txt").write_text(f"mutant {index}\n")
        (repo / "build.sh").write_text("#!/usr/bin/env bash\nset -euo pipefail\ncp source.txt executable\n")
        (repo / "build.sh").chmod(0o755)

    build_root = tmp_path / "build"
    result = subprocess.run(
        ["bash", "-c", _localize(_build_command(tmp_path, 3)[1], tmp_path, workspace, build_root)],
        capture_output=True, text=True,
    )

    assert result.returncode == 0, result.stderr
    for index in range(1, 4):
        assert (build_root / f"repo_{index}" / "executable").read_text() == f"mutant {index}\n"
        assert (workspace / f"repo_{index}" / "executable").read_text() == f"mutant {index}\n"
        assert (build_root / f".repo_{index}.source-hash").read_text().strip()

    # A repair attempt must keep unchanged staged builds and restage only edited sources.
    (build_root / "repo_1" / "marker").write_text("kept\n")
    (build_root / "repo_2" / "marker").write_text("dropped\n")
    (workspace / "repo_2" / "source.txt").write_text("edited\n")
    repair = subprocess.run(
        ["bash", "-c", _localize(_build_command(tmp_path, 3, attempt=1)[1], tmp_path, workspace, build_root)],
        capture_output=True, text=True,
    )

    assert repair.returncode == 0, repair.stderr
    assert (build_root / "repo_1" / "marker").is_file()
    assert not (build_root / "repo_2" / "marker").exists()
    assert (workspace / "repo_2" / "executable").read_text() == "edited\n"
