from __future__ import annotations

import re
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts" / "docker"
CLEANUP = SCRIPTS / "cleanup_programbench_docker.sh"
INSTALL_SCRIPTS = (
    SCRIPTS / "install_codex_cleanroom.sh",
    SCRIPTS / "install_claude_cleanroom.sh",
    SCRIPTS / "install_agent_cleanroom.sh",
    SCRIPTS / "install_task_patched.sh",
)


def removed_tags() -> set[str]:
    """Tags cleanup_task_images deletes, read from its removal loop."""
    body = CLEANUP.read_text().split("cleanup_task_images()")[1]
    loop = body.split("for image_ref in")[1].split("; do")[0]
    return set(re.findall(r'programbench/\$\{image_task\}:([a-z_]+)', loop))


def test_cleanup_preserves_the_only_tag_that_needs_a_registry_pull():
    """task_cleanroom is the base every other image builds from.

    Deleting it forces a ~2GB re-pull per task on the next build, which is the
    exact cost the keep-one-tag policy exists to avoid.
    """
    assert "task_cleanroom" not in removed_tags()


def test_cleanup_removes_the_now_unused_task_image():
    """Nothing builds from :task since the grading image was rebased.

    Keeping it costs ~2GB per task and buys nothing, and it was previously kept
    on the stale rationale that every other tag rebuilt from it.
    """
    assert "task" in removed_tags()


def test_cleanup_removes_every_locally_built_tag():
    """A tag missing from the list leaks: it is never reclaimed.

    task_cleanroom_claude leaked this way -- it was added after the list was
    written and nobody updated the list.
    """
    assert {
        "task_cleanroom_codex",
        "task_cleanroom_claude",
        "task_cleanroom_gemini",
        "task_cleanroom_qwen",
        "task_patched",
        "task_mutantbuild",
    } <= removed_tags()


def test_preserved_tag_is_what_the_install_scripts_build_from():
    """The keep-list and the build bases must name the same tag.

    They are edited in different files, so a change to one silently makes the
    other wrong: either a re-pull on every build, or a retained image nothing
    uses.
    """
    preserved = "task_cleanroom"
    for script in INSTALL_SCRIPTS:
        text = script.read_text()
        assert re.search(rf"(default_base_tag|BASE_TAG:-)\s*=?\s*{preserved}\b", text), script.name
