#!/usr/bin/env python3
"""Build-scoped APT acceleration; ordinary/unsupported APT commands pass through."""
from __future__ import annotations

import fcntl
import os
from pathlib import Path
import re
import subprocess
import sys
import time


def install_packages(args: list[str]) -> list[str] | None:
    if not args or args[0] != "install":
        return None
    packages = []
    for arg in args[1:]:
        if arg in {"-y", "--yes", "--no-install-recommends", "-q", "-qq"}:
            continue
        if not re.fullmatch(r"[a-z0-9][a-z0-9+.-]*(?::[a-z0-9-]+)?", arg):
            return None
        packages.append(arg)
    return packages or None


def installed(packages: list[str], query: str) -> bool:
    result = subprocess.run(
        [query, "-W", "-f=${binary:Package} ${Status}\n", *packages],
        capture_output=True, text=True,
    )
    lines = result.stdout.splitlines()
    return result.returncode == 0 and len(lines) == len(packages) and all(
        line.endswith(" install ok installed") for line in lines
    )


def main() -> int:
    command = Path(sys.argv[0]).name
    args = sys.argv[1:]
    real = str(Path(os.environ.get("PROGRAMBENCH_APT_BIN_DIR", "/usr/bin")) / command)
    cache = os.environ.get("PROGRAMBENCH_BUILD_APT_CACHE")
    if not cache:
        return subprocess.call([real, *args])
    root = Path(cache)
    root.mkdir(parents=True, exist_ok=True)
    # Share the existing lock with any non-cached apt invocations in this container.
    lock = Path(os.environ.get("PROGRAMBENCH_APT_LOCK_FILE", "/var/lock/programbench-apt.lock"))
    query = os.environ.get("PROGRAMBENCH_DPKG_QUERY", "/usr/bin/dpkg-query")
    packages = install_packages(args)
    started = time.monotonic()
    outcome = "executed"
    with lock.open("a") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        acquired = time.monotonic()
        marker = root / "updated"
        if args == ["update"] and marker.exists():
            outcome, rc = "reused", 0
        elif packages and installed(packages, query):
            outcome, rc = "reused", 0
        else:
            # build.sh may delete APT lists after its last installation. If a
            # later repo requests new packages, refresh before that install.
            rc = 0
            if args and args[0] == "install" and marker.exists():
                rc = subprocess.call([real, "update"])
            if rc == 0:
                rc = subprocess.call([real, *args])
            if rc == 0 and args == ["update"]:
                marker.touch()
            elif rc != 0 or (packages is None and args != ["update"]):
                # Failed or unknown commands can invalidate cached setup.
                marker.unlink(missing_ok=True)
    print(
        f"[mutant-build-apt] command={command} action={args[0] if args else ''} "
        f"outcome={outcome} wait_second={acquired-started:.3f} "
        f"duration_second={time.monotonic()-started:.3f}", flush=True,
    )
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
