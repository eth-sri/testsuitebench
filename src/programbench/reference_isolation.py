"""Reference-artifact isolation shared by standalone and package agent runners.

Only trusted task images and cleanroom inputs are supported. This removes the
benchmark's reference artifacts; it is not a sandbox for arbitrary host mounts
or task images containing undisclosed copies of the original program.
"""

from __future__ import annotations

import os
import shlex
import shutil
import stat
from pathlib import Path


REFERENCE_NAMES = frozenset({
    "executable", "executable_cov", "executable_nocov", "_inject_exe",
    ".programbench-ground-truth", ".programbench-ground-truth-executable",
    ".programbench-mutant-executable", "programbench-executable-under-test",
})


def is_reference_name(name: str) -> bool:
    return name in REFERENCE_NAMES or name.startswith("programbench_reference_executable")


def stage_cleanroom(source: Path | None, destination: Path, *, with_executable: bool = False) -> Path | None:
    """Stage inputs before mounting, without hidden references or history.

    Symlinks must remain inside the input tree and cannot alias excluded files.
    Hard links to excluded binaries are omitted too. Explicit binary mode keeps
    the supplied executable but still strips Git history and harness backups.
    """
    if source is None:
        return None
    source = source.resolve()
    excluded_inodes: set[tuple[int, int]] = set()

    def excluded(path: Path) -> bool:
        return any(
            part == ".git" or (is_reference_name(part) and not (with_executable and part == "executable" and path.relative_to(source) == Path("executable")))
            for part in path.relative_to(source).parts
        )

    for directory, dirs, files in os.walk(source, followlinks=False):
        dirs[:] = [name for name in dirs if name != ".git"]
        for name in files:
            path = Path(directory) / name
            if (excluded(path) or is_reference_name(name)) and path.is_file():
                info = path.stat()
                excluded_inodes.add((info.st_dev, info.st_ino))

    def ignore(directory: str, names: list[str]) -> list[str]:
        ignored = []
        for name in names:
            path = Path(directory) / name
            if excluded(path):
                ignored.append(name)
                continue
            if path.is_symlink():
                target = path.resolve()
                if not target.is_relative_to(source) or excluded(target) or not target.exists():
                    ignored.append(name)
                    continue
                # Preserve safe relative links only; absolute links would point
                # outside the staged mount in the agent's filesystem.
                if os.path.isabs(os.readlink(path)):
                    ignored.append(name)
                    continue
            if path.is_file():
                info = path.stat()
                if (info.st_dev, info.st_ino) in excluded_inodes and not (with_executable and name == "executable" and not path.is_symlink()):
                    ignored.append(name)
        return ignored

    def copy_file(src: str, dest: str) -> str:
        path = Path(src)
        mode = stat.S_IMODE(path.stat().st_mode)
        unreadable = not os.access(path, os.R_OK)
        try:
            if unreadable:
                path.chmod(mode | stat.S_IRUSR)
            result = shutil.copy2(src, dest)
            Path(dest).chmod(0o111 if with_executable and path.name == "executable" else mode)
            return result
        finally:
            if unreadable:
                path.chmod(mode)

    shutil.copytree(source, destination, ignore=ignore, symlinks=True, copy_function=copy_file)
    return destination


def reference_cleanup_command() -> str:
    """Fail closed if an image reference or stale backup cannot be removed."""
    paths = [f"/workspace/{name}" for name in sorted(REFERENCE_NAMES)]
    paths += [f"/tmp/programbench_cleanroom/{name}" for name in sorted(REFERENCE_NAMES)]
    paths += [
        "/workspace/.git", "/tmp/programbench_cleanroom/.git",
        "/tmp/_inject_exe", "/tmp/programbench-executable-under-test",
    ]
    words = " ".join(shlex.quote(path) for path in paths)
    words += (
        " /workspace/programbench_reference_executable* /tmp/programbench_reference_executable*"
        " /tmp/programbench_cleanroom/programbench_reference_executable*"
    )
    return f"""rm -rf -- {words}
for reference_path in {words}; do
    if [ -e "$reference_path" ] || [ -L "$reference_path" ]; then
        echo "Reference isolation failed: $reference_path remains accessible" >&2
        exit 1
    fi
done"""


def solve_workspace_setup(mode: str) -> str:
    """Stage the specification, retaining a reference only in explicit mode."""
    if mode not in {"spec-only", "with-test", "with-test-force", "with-executable"}:
        raise ValueError(f"Unknown solve mode: {mode}")
    cleanup = reference_cleanup_command() if mode != "with-executable" else ""
    return f"""{cleanup}
if [ -d /tmp/programbench_cleanroom ]; then
    reference_executable=/tmp/programbench_reference_executable
    rm -f "$reference_executable"
    if [ "$mode" = "with-executable" ] && [ -e /workspace/executable ]; then
        cp -a /workspace/executable "$reference_executable"
    fi
    find /workspace -mindepth 1 -maxdepth 1 -exec rm -rf {{}} +
    if [ "$mode" = "with-executable" ]; then
        tar -C /tmp/programbench_cleanroom -cf - . | tar -C /workspace -xf -
        if [ ! -e /workspace/executable ] && [ -e "$reference_executable" ]; then
            cp -a "$reference_executable" /workspace/executable
        fi
    else
        tar -C /tmp/programbench_cleanroom --exclude=./executable --exclude=executable -cf - . | tar -C /workspace -xf -
        rm -f /workspace/executable
    fi
fi
if [ "$mode" = "with-executable" ] && [ ! -e /workspace/executable ]; then
    echo "with-executable mode requires ./executable in the cleanroom or base image" >&2
    exit 1
fi
{cleanup}
# Reference isolation complete.
"""


# The agent owns its build files, but never the reference inode. Dropping all
# capabilities also prevents DAC bypass, chown, ptrace and switching identities.
AGENT_UID = 61000
AGENT_EXEC = (
    f"/usr/bin/setpriv --reuid={AGENT_UID} --regid={AGENT_UID} --clear-groups "
    "--bounding-set=-all --inh-caps=-all --ambient-caps=-all --no-new-privs"
)


def stage_reference(source: Path, destination: Path) -> Path:
    """Make an execute-only mount source without modifying the caller's file."""
    mode = stat.S_IMODE(source.stat().st_mode)
    unreadable = not os.access(source, os.R_OK)
    try:
        if unreadable:
            source.chmod(mode | stat.S_IRUSR)
        shutil.copyfile(source, destination)
    finally:
        if unreadable:
            source.chmod(mode)
    destination.chmod(0o111)
    return destination


def reference_guard_setup() -> str:
    """Trusted bootstrap, before any agent or generated code is executed.

    Only ELF references support execute-without-read; shell/Python scripts need
    interpreter reads and are deliberately rejected instead of weakening access.
    """
    return r"""set -eu
/usr/bin/python3 - <<'PROGRAMBENCH_PROTECT_REFERENCE' || exit $?
import errno, os, pathlib, shutil
uid = 61000
ref = pathlib.Path('/workspace/executable')
if ref.is_symlink() or not ref.is_file() or ref.open('rb').read(4) != b'\x7fELF':
    raise SystemExit('Reference protection requires a regular ELF executable')
# Remove auxiliary copies; the two read-only input mounts are validated below.
for root in (pathlib.Path('/workspace'), pathlib.Path('/tmp')):
    for p in root.iterdir():
        if p == ref or p.name == 'programbench_cleanroom':
            continue
        if p.name in ('executable_cov', 'executable_nocov', '_inject_exe', '.git',
                      '.programbench-ground-truth', '.programbench-ground-truth-executable',
                      '.programbench-mutant-executable', 'programbench-executable-under-test') or p.name.startswith('programbench_reference_executable'):
            try:
                if p.is_dir() and not p.is_symlink(): shutil.rmtree(p)
                else: p.unlink()
            except OSError as e:
                if p != pathlib.Path('/tmp/programbench_reference_executable') or e.errno not in (errno.EBUSY, errno.EROFS): raise
for p in (pathlib.Path('/tmp/programbench_reference_executable'), pathlib.Path('/tmp/programbench_cleanroom/executable')):
    if p.exists() and (p.is_symlink() or not p.is_file() or p.stat().st_mode & 0o444 or p.stat().st_uid == uid):
        raise SystemExit('Unsafe reference source mount: ' + str(p))
# Keep SDK configuration and credentials, but give the session its own home.
home = pathlib.Path('/tmp/programbench-agent-home')
if home.exists(): shutil.rmtree(home)
home.mkdir(mode=0o700)
old_home = pathlib.Path(os.environ.get('HOME', '/root'))
old_home.chmod(old_home.stat().st_mode | 0o011)
for p in old_home.iterdir():
    if p.name in ('.cache', '.npm'):
        (home / p.name).mkdir()
        continue
    if p.name in ('.cargo', '.rustup', '.local'):
        (home / p.name).symlink_to(p, target_is_directory=p.is_dir())
        continue
    if p.is_dir(): shutil.copytree(p, home / p.name, symlinks=True)
    else: shutil.copy2(p, home / p.name)
claude = pathlib.Path(os.environ.get('CLAUDE_CONFIG_DIR', '/tmp/programbench-claude-config'))
if claude.is_dir(): shutil.copytree(claude, home / '.claude', dirs_exist_ok=True)
# The workspace and agent home are writable. System binaries remain root-owned.
for root in (pathlib.Path('/workspace'), home):
    os.chown(root, uid, uid)
    for directory, dirs, files in os.walk(root, followlinks=False):
        for name in dirs + files:
            p = pathlib.Path(directory) / name
            if p != ref: os.chown(p, uid, uid, follow_symlinks=False)
os.chown(ref, 0, 0)
ref.chmod(0o111)
PROGRAMBENCH_PROTECT_REFERENCE
command -v /usr/bin/setpriv >/dev/null
# Reference permission guard ready.
"""


def reference_agent_command(command: str) -> str:
    """Run an entire agent/postflight shell after irrevocably dropping privilege."""
    return (
        AGENT_EXEC + " /usr/bin/env HOME=/tmp/programbench-agent-home "
        "CODEX_HOME=/tmp/programbench-agent-home/.codex "
        "CLAUDE_CONFIG_DIR=/tmp/programbench-agent-home/.claude "
        "/bin/bash -c " + shlex.quote(command)
    )


def guard_reference_session(script: str, *, enabled: bool) -> str:
    if not enabled:
        return script
    # All launchers read the prompt only after completing trusted setup.
    marker = 'prompt=$(cat /tmp/programbench_prompt.txt)'
    before, after = script.split(marker, 1)
    return (
        before + reference_guard_setup()
        + "\nexport mode codex_model reasoning claude_model effort\nexec "
        + reference_agent_command("set -euo pipefail\n" + marker + after) + "\n"
    )
