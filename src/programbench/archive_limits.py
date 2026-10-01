"""Bound archive contents before compression, including tar overhead."""

import shlex

MAX_ARCHIVE_BYTES = 1_000_000_000


def bounded_archive_command(
    excludes: tuple[str, ...],
    *,
    workspace: str,
    archive_path: str,
    members: tuple[str, ...] = (".",),
    limit_bytes: int = MAX_ARCHIVE_BYTES,
) -> str:
    # Do not use sparse tar encoding: holes must count toward extracted size.
    compressor = f"""import gzip, sys
total = 0
with gzip.open({archive_path!r}, 'wb') as output:
    while chunk := sys.stdin.buffer.read(min(1024 * 1024, {limit_bytes} - total)):
        total += len(chunk)
        if total >= {limit_bytes}:
            sys.exit('Uncompressed archive must be below {limit_bytes} bytes')
        output.write(chunk)
"""
    tar_args = " ".join(shlex.quote(arg) for arg in (
        "tar", *(f"--exclude={path}" for path in excludes),
        "-cf", "-", "-C", workspace, *members,
    ))
    script = f"""set -o pipefail
if {tar_args} | python3 -c {shlex.quote(compressor)}; then
    exit 0
else
    rm -f {shlex.quote(archive_path)}
    exit 1
fi"""
    return "bash -c " + shlex.quote(script)
