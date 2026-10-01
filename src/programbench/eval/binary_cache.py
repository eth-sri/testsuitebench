"""Content-addressed checkpoints for explicitly resumable binary evaluations."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import stat
import tempfile


def digest_path(path: Path) -> str:
    digest = hashlib.sha256()
    entries = [path]
    if path.is_dir() and not path.is_symlink():
        entries += sorted(path.rglob("*"))
    for entry in entries:
        info = entry.lstat()
        name = "." if entry == path else entry.relative_to(path).as_posix()
        digest.update((name + "\0" + str(stat.S_IMODE(info.st_mode)) + "\0").encode())
        if entry.is_symlink():
            digest.update(b"link\0" + os.fsencode(os.readlink(entry)))
        elif entry.is_file():
            digest.update(f"file\0{info.st_size}\0".encode())
            with entry.open("rb") as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(chunk)
        elif entry.is_dir():
            digest.update(b"dir\0")
        else:
            raise ValueError(f"Cannot cache an evaluation with special input {entry}")
    return digest.hexdigest()


def atomic_write(path: Path, contents: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        try:
            stream.write(contents)
            stream.flush()
            os.fsync(stream.fileno())
            stream.close()
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)
