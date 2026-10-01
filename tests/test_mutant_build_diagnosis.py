from pathlib import Path

import pytest

from programbench import mutants
from programbench.source_build import CLEAR_BUILD_ROOT_SHELL

UNIVERSAL_FAILURE = (
    "[mutant-build-progress] completed=1/2 compiled=0 reused=0 failed=1 last=repo_1 outcome=failed\n"
    "[mutant-build-progress] completed=2/2 compiled=0 reused=0 failed=2 last=repo_2 outcome=failed\n"
    "error[E0308]: mismatched types: QuerySource::from expected String, found &str\n"
)
PARTIAL_FAILURE = (
    "[mutant-build-progress] completed=1/2 compiled=1 reused=0 failed=0 last=repo_1 outcome=compiled\n"
    "[mutant-build-progress] completed=2/2 compiled=1 reused=0 failed=1 last=repo_2 outcome=failed\n"
)


class FakeEnv:
    def __init__(self, build_output: str) -> None:
        self.build_output = build_output
        self.commands: list[str] = []

    def copy_in(self, local_path: Path, container_path: str) -> None:
        pass

    def execute(self, command: str, **kwargs: object) -> dict[str, object]:
        self.commands.append(command)
        if "build_mutant_repos_parallel.sh" in command and "--jobs" in command:
            return {"returncode": 1, "stdout": "", "output": self.build_output}
        return {"returncode": 0, "stdout": "", "output": ""}

    def cleanup(self) -> None:
        pass


@pytest.mark.parametrize(
    ("build_output", "expected"),
    [
        # compiled=0 everywhere cannot be caused by per-repository mutations.
        (UNIVERSAL_FAILURE, "every mutant repository failed to build"),
        (PARTIAL_FAILURE, "failed to rebuild mutant repositories"),
    ],
)
def test_distinguishes_broken_baseline_from_individual_mutant_failures(
    tmp_path, monkeypatch, build_output, expected
):
    for name in ("repo_1", "repo_2"):
        (tmp_path / name).mkdir()
    monkeypatch.setattr(mutants, "ContainerEnvironment", lambda **kwargs: FakeEnv(build_output))

    with pytest.raises(RuntimeError, match=expected) as raised:
        mutants._rebuild_mutant_repositories_in_container(
            instance_id="org__repo.123",
            target_root=tmp_path,
            repo_names=["repo_1", "repo_2"],
            image="image",
            docker_executable="docker",
            docker_cpus=4,
            build_jobs=2,
            timeout=60,
            run_args=None,
        )

    assert "E0308" in str(raised.value) or "compiled=1" in str(raised.value)


def test_build_root_is_cleared_even_when_the_build_fails(tmp_path, monkeypatch):
    """Mutant target/ trees are hundreds of GB per task and live on a host bind
    mount, so a build that leaves them behind holds that space until the same
    task happens to build again."""
    for name in ("repo_1", "repo_2"):
        (tmp_path / name).mkdir()
    env = FakeEnv(UNIVERSAL_FAILURE)
    monkeypatch.setattr(mutants, "ContainerEnvironment", lambda **kwargs: env)

    with pytest.raises(RuntimeError):
        mutants._rebuild_mutant_repositories_in_container(
            instance_id="org__repo.123",
            target_root=tmp_path,
            repo_names=["repo_1", "repo_2"],
            image="image",
            docker_executable="docker",
            docker_cpus=4,
            build_jobs=2,
            timeout=60,
            run_args=None,
        )

    assert env.commands[-1] == CLEAR_BUILD_ROOT_SHELL
    assert CLEAR_BUILD_ROOT_SHELL in env.commands[0]
