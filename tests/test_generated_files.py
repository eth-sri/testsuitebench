from __future__ import annotations

from pathlib import Path

import pytest

from programbench import generated_files
from programbench.constants import GENERATED_FILES_NAME
from programbench.generated_files import load_generated_files, record_generated_files


class _Env:
    def __init__(self, returncode: int) -> None:
        self.returncode = returncode
        self.copied_out = False

    def execute(self, command: str, timeout: int | None = None) -> dict[str, object]:
        if "build.sh" not in command:
            return {"returncode": 0, "output": ""}
        return {"returncode": self.returncode, "output": "go: requires go >= 1.26.0"}

    def copy_in(self, *_args) -> None:
        pass

    def copy_out_file(self, _source, destination) -> None:
        self.copied_out = True
        Path(destination).write_text("shell.c\nconfig.log\n")

    def cleanup(self) -> None:
        pass


@pytest.fixture
def env(monkeypatch: pytest.MonkeyPatch):
    created: list[_Env] = []

    def build(returncode: int):
        monkeypatch.setattr(generated_files, "build_cache_args", lambda *_: ([], {}))
        monkeypatch.setattr(generated_files, "resolve_build_image", lambda image, **_: image)
        instance = _Env(returncode)
        created.append(instance)
        monkeypatch.setattr(generated_files, "ContainerEnvironment", lambda **_: instance)
        return instance

    return build


def test_record_generated_files_writes_and_then_reuses_the_manifest(tmp_path: Path, env) -> None:
    container = env(0)

    assert record_generated_files(task="org__repo.rev", implementation=tmp_path, image="img") == {
        "task": "org__repo.rev", "status": "recorded", "generated": 2,
    }
    assert container.copied_out
    assert load_generated_files(tmp_path) == ["shell.c", "config.log"]

    # A second run must not rebuild: the manifest is the cache.
    second = env(0)
    assert record_generated_files(task="org__repo.rev", implementation=tmp_path, image="img")["status"] == "cached"
    assert not second.copied_out


def test_record_generated_files_leaves_no_manifest_when_the_build_no_longer_reproduces(
    tmp_path: Path, env, caplog: pytest.LogCaptureFixture,
) -> None:
    container = env(1)

    with caplog.at_level("WARNING", logger="programbench.generated_files"):
        status = record_generated_files(task="sheepla__pingu.926d475", implementation=tmp_path, image="img")

    # Nothing is withheld, so mutant generation behaves exactly as it did before.
    assert status == {"task": "sheepla__pingu.926d475", "status": "unavailable", "generated": 0}
    assert not (tmp_path / GENERATED_FILES_NAME).exists()
    assert load_generated_files(tmp_path) == []
    assert not container.copied_out
    assert "continuing without a manifest" in caplog.text
