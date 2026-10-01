from __future__ import annotations

import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WRAPPER = ROOT / "scripts" / "docker" / "apt-flock-wrapper.sh"


def test_agent_images_install_apt_flock_wrapper() -> None:
    """One Dockerfile now builds every variant, so one copy of the wrapper."""
    dockerfile = (ROOT / "scripts" / "docker" / "programbench_image.Dockerfile").read_text()

    assert "util-linux" in dockerfile
    assert "COPY scripts/docker/apt-flock-wrapper.sh" in dockerfile
    assert "/usr/local/bin/apt-get" in dockerfile


def test_cached_agent_images_require_the_wrapper() -> None:
    """A cached image predating the wrapper must be rebuilt, not reused.

    Both install scripts delegate that decision to one shared probe. When they each carried
    their own, they checked different properties and the same image could be fresh under one
    and stale under the other, so the check is pinned to the probe rather than to either script.
    """
    probe = (ROOT / "scripts" / "docker" / "programbench_image_probe.sh").read_text()

    for binary in ("apt", "apt-get"):
        assert f'readlink -f /usr/local/bin/{binary})\\" = /usr/local/libexec/programbench-apt-flock' in probe

    for name in ("install_codex_cleanroom.sh", "install_claude_cleanroom.sh", "install_agent_cleanroom.sh"):
        script = (ROOT / "scripts" / "docker" / name).read_text()
        assert ". scripts/docker/programbench_image_probe.sh" in script, name
        # The cache hit itself must be gated on the probe; an image that fails it falls through
        # to a rebuild rather than being reused.
        assert "if programbench_image_is_fresh " in script, name


def test_wrapper_forwards_to_matching_real_command(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    output = tmp_path / "arguments"
    target = bin_dir / "apt-get"
    target.write_text(f"#!/bin/sh\nprintf '%s\\n' \"$@\" > {output}\n")
    target.chmod(0o755)
    wrapped = tmp_path / "apt-get"
    wrapped.symlink_to(WRAPPER)

    env = {
        **os.environ,
        "PROGRAMBENCH_APT_BIN_DIR": str(bin_dir),
        "PROGRAMBENCH_APT_LOCK_FILE": str(tmp_path / "apt.lock"),
    }
    subprocess.run([wrapped, "install", "-y", "example"], env=env, check=True)

    assert output.read_text().splitlines() == ["install", "-y", "example"]
