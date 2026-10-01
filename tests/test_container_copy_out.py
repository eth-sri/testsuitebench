# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

import stat
from pathlib import Path

import pytest

from programbench.container import ContainerEnvironment

STUB = """#!/bin/bash
shift 2
tar --no-same-owner -C "$FAKE_SRC" -cf - .
case "$FAKE_MODE" in
  warn) echo "tar: ./target/release/.fingerprint/either-5c75: file changed as we read it" >&2; exit 1;;
  fatal) echo "tar: ./nope: Cannot open: No such file or directory" >&2; exit 2;;
  dockerfail) echo "Error response from daemon: container not running" >&2; exit 1;;
esac
"""


@pytest.fixture
def env(tmp_path, monkeypatch):
    source = tmp_path / "repo"
    (source / "target" / "release").mkdir(parents=True)
    (source / "executable").write_text("binary")
    (source / "target" / "release" / "app").write_text("built")
    stub = tmp_path / "fakedocker"
    stub.write_text(STUB)
    stub.chmod(stub.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("FAKE_SRC", str(source))

    environment = ContainerEnvironment.__new__(ContainerEnvironment)
    environment.executable = str(stub)
    environment.container_id = "deadbeef"
    return environment


def test_copy_out_dir_tolerates_tar_changed_file_warning(env, tmp_path, monkeypatch, caplog):
    monkeypatch.setenv("FAKE_MODE", "warn")
    env.copy_out_dir("/workspace/mutants/repo_1", tmp_path / "out")
    assert sorted(
        p.relative_to(tmp_path / "out").as_posix() for p in (tmp_path / "out").rglob("*") if p.is_file()
    ) == ["executable", "target/release/app"]
    assert "file changed as we read it" in caplog.text


@pytest.mark.parametrize(("mode", "expected"), [
    ("fatal", "docker rc=2"),
    ("dockerfail", "container not running"),
])
def test_copy_out_dir_still_fails_on_real_errors(env, tmp_path, monkeypatch, mode, expected):
    monkeypatch.setenv("FAKE_MODE", mode)
    with pytest.raises(RuntimeError, match=expected):
        env.copy_out_dir("/workspace/mutants/repo_1", tmp_path / "out")
    assert not (tmp_path / "out").exists()
