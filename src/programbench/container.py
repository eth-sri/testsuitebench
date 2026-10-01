# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

import logging
import os
import posixpath
import shlex
import shutil
import subprocess
import threading
import tempfile
import time
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

from programbench.container_cleanup import container_labels, remove_container

from programbench.constants import (
    DOCKER_CP_TIMEOUT,
    DOCKER_EXECUTABLE,
    DOCKER_RUN_TIMEOUT,
    REPO_ROOT,
    cleanroom_codex_image,
)

log = logging.getLogger(__name__)

# GNU tar exits 1 for this non-fatal warning and 2 for real errors.
_TAR_CHANGED_WARNING = "file changed as we read it"


def _env_int(name: str, default: int) -> int:
    try:
        return max(0, int(os.environ.get(name, default)))
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return max(0.0, float(os.environ.get(name, default)))
    except ValueError:
        return default


def _is_transient_container_start_failure(result: subprocess.CompletedProcess) -> bool:
    stderr = (result.stderr or "").lower()
    return any(
        marker in stderr
        for marker in (
            "unable to create session key",
            "unable to join session keyring",
            "failed to create shim task",
            "disk quota exceeded",
        )
    )


def _cleanup_failed_container(executable: str, stdout: str) -> None:
    failed_container_id = stdout.strip().splitlines()[0] if stdout.strip() else ""
    if not failed_container_id:
        return
    remove_container(executable, failed_container_id)


def _format_subprocess_failure(action: str, result: subprocess.CompletedProcess) -> str:
    stdout = (result.stdout or "").strip()
    stderr = (result.stderr or "").strip()
    return f"{action} failed (rc={result.returncode}, stdout={stdout!r}, stderr={stderr!r})"


class ContainerEnvironment:
    """Manage a long-running container for command execution and file injection."""

    def __init__(
        self,
        *,
        image: str,
        cwd: str = "/",
        executable: str = "docker",
        timeout: int = 30,
        cpus: int = 10,
        env: dict[str, str] | None = None,
        run_args: list[str] | None = None,
    ):
        self.cwd = cwd
        self.executable = executable
        self.default_timeout = timeout
        self.cpus = cpus
        self._name = f"programbench-{uuid.uuid4().hex[:12]}"
        run_args = list(run_args or [])
        # Docker enforces --cpus as a CFS quota, so nproc inside the container still
        # reports every host core and build tools fan out far past the quota.
        env_dict = {
            "PYTEST_XDIST_AUTO_NUM_WORKERS": str(cpus),
            "MAKEFLAGS": f"-j{cpus}",
            "CARGO_BUILD_JOBS": str(cpus),
            "CMAKE_BUILD_PARALLEL_LEVEL": str(cpus),
            "GOMAXPROCS": str(cpus),
            "RAYON_NUM_THREADS": str(cpus),
            "OMP_NUM_THREADS": str(cpus),
            **(env or {}),
        }
        env_args: list[str] = []
        for key, value in env_dict.items():
            env_args.extend(["-e", f"{key}={value}"])
        cmd = [
            executable,
            "run",
            "-d",
            "--init",
            "--name",
            self._name,
            *container_labels(),
            "--entrypoint",
            "",
            "-w",
            cwd,
            "--cpus",
            str(cpus),
            *env_args,
            *run_args,
            image,
            "sleep",
            "infinity",
        ]
        log.debug("Starting container: %s", " ".join(cmd))
        retries = _env_int("PROGRAMBENCH_DOCKER_RUN_RETRIES", 5)
        retry_delay = _env_float("PROGRAMBENCH_DOCKER_RUN_RETRY_DELAY", 5.0)
        result = None
        for attempt in range(retries + 1):
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=DOCKER_RUN_TIMEOUT)
            if result.returncode == 0:
                self.container_id = result.stdout.strip()
                return
            _cleanup_failed_container(executable, result.stdout or "")
            if attempt >= retries or not _is_transient_container_start_failure(result):
                break
            delay = retry_delay * min(6, 2 ** attempt)
            log.warning(
                "Container start failed with a transient Docker error; retrying in %.1fs (%d/%d): %s",
                delay,
                attempt + 1,
                retries,
                (result.stderr or "").strip(),
            )
            time.sleep(delay)
        assert result is not None
        raise RuntimeError(_format_subprocess_failure("start container", result))

    def execute(
        self,
        command: str,
        *,
        timeout: int | None = None,
        output_callback: Callable[[str, str], None] | None = None,
    ) -> dict[str, Any]:
        """Run a shell command inside the container, optionally streaming output lines."""
        timeout = timeout or self.default_timeout
        cmd = [
            self.executable,
            "exec",
            "-w",
            self.cwd,
            self.container_id,
            "bash",
            "-lc",
            command,
        ]
        if output_callback is None:
            try:
                result = subprocess.run(
                    cmd,
                    stdin=subprocess.DEVNULL,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                )
                output = result.stdout + result.stderr
                return {
                    "output": output,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "returncode": result.returncode,
                    "exception_info": "",
                }
            except subprocess.TimeoutExpired:
                return {
                    "output": "",
                    "stdout": "",
                    "stderr": "",
                    "returncode": -1,
                    "exception_info": f"Command timed out after {timeout}s",
                }

        process = subprocess.Popen(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        chunks: dict[str, list[str]] = {"stdout": [], "stderr": []}

        def read_stream(stream_name: str) -> None:
            stream = getattr(process, stream_name)
            assert stream is not None
            try:
                for line in stream:
                    chunks[stream_name].append(line)
                    try:
                        output_callback(stream_name, line)
                    except Exception:
                        log.exception("Output callback failed for %s", stream_name)
            finally:
                stream.close()

        threads = [
            threading.Thread(target=read_stream, args=(stream_name,), daemon=True)
            for stream_name in ("stdout", "stderr")
        ]
        for thread in threads:
            thread.start()

        exception_info = ""
        try:
            returncode = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            process.kill()
            returncode = process.wait()
            exception_info = f"Command timed out after {timeout}s"
        finally:
            for thread in threads:
                thread.join()

        stdout = "".join(chunks["stdout"])
        stderr = "".join(chunks["stderr"])
        return {
            "output": stdout + stderr,
            "stdout": stdout,
            "stderr": stderr,
            "returncode": -1 if exception_info else returncode,
            "exception_info": exception_info,
        }

    def copy_in(
        self,
        local_path: Path,
        container_path: str,
        *,
        excludes: list[str] | None = None,
    ) -> None:
        """Copy a local file or directory tree into the container.

        Directories and regular files are streamed via
        ``tar | docker exec -i tar --no-same-owner -xf -`` so unusual entries
        survive: escape symlinks (skeema's
        cfgsymlinks/invalidrel/.skeema → ../../../etc/bashrc fixture),
        modes, hardlinks, sticky bits, and sparse-file holes. It also avoids
        ``docker cp`` trying to restore host uid/gid values that rootless containers may not be able to
        represent. The docker daemon validates symlinks in both
        ``docker cp <dir>`` and ``docker cp - <c>:<dest>`` (stream mode);
        routing through the container's own tar bypasses that check.
        """
        if local_path.is_dir():
            self._stream_tar_in(
                container_path,
                producer=[
                    "tar",
                    "--sparse",
                    "-C",
                    str(local_path),
                    *(f"--exclude={pattern}" for pattern in (excludes or [])),
                    "-cf",
                    "-",
                    ".",
                ],
            )
            return
        self._stream_file_in(local_path, container_path)

    def _stream_file_in(self, local_path: Path, container_path: str) -> None:
        """Copy one local file to an exact container path without ``docker cp``.

        A symlink is followed (``tar -h``) so the container gets the file itself. The
        HuggingFace cache serves every file as a symlink into ``blobs/``, which would
        otherwise arrive as a dangling link.
        """
        tmp_dir = f"/tmp/programbench-copy-{uuid.uuid4().hex}"
        self._stream_tar_in(
            tmp_dir,
            producer=["tar", "--sparse", "-h", "-C", str(local_path.parent), "-cf", "-", "--", local_path.name],
        )

        dest_dir = posixpath.dirname(container_path) or "."
        src_path = posixpath.join(tmp_dir, local_path.name)
        script = (
            "set -e; "
            f"mkdir -p {shlex.quote(dest_dir)}; "
            f"mv -f {shlex.quote(src_path)} {shlex.quote(container_path)}; "
            f"rm -rf {shlex.quote(tmp_dir)}"
        )
        cmd = [self.executable, "exec", self.container_id, "bash", "-lc", script]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=DOCKER_CP_TIMEOUT)
        if result.returncode != 0:
            raise RuntimeError(_format_subprocess_failure("file move in container", result))

    def copy_in_many(self, root: Path, names: list[str], container_path: str) -> None:
        """Transfer selected immediate children in one tar/Docker invocation."""
        if any(not name or name in {".", ".."} or "/" in name or "\\" in name for name in names):
            raise ValueError("copy_in_many requires immediate child names")
        with tempfile.NamedTemporaryFile() as listing:
            listing.write(b"\0".join(os.fsencode(name) for name in names) + b"\0")
            listing.flush()
            self._stream_tar_in(
                container_path,
                producer=["tar", "--sparse", "-C", str(root), "-cf", "-", "--null", "-T", listing.name],
            )

    def copy_in_tar(self, tar_path: Path, container_path: str) -> None:
        """Stream an on-disk tar(.gz) into the container via the container's tar.

        Avoids host-side extract entirely. Same symlink/mode-preserving
        behaviour as ``copy_in`` for directories. Lets the container's tar
        decompress (passes ``-z`` for ``.tar.gz`` / ``.tgz``).
        """
        is_gz = tar_path.name.endswith((".tar.gz", ".tgz")) or tar_path.suffix == ".gz"
        with tar_path.open("rb") as f:
            self._stream_tar_in(container_path, stdin_stream=f, compressed=is_gz)

    def copy_out_file(self, container_path: str, local_path: Path) -> None:
        """Copy one regular file out of the container to an exact local path."""
        local_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = local_path.with_name(f".{local_path.name}.tmp-{uuid.uuid4().hex}")
        result = subprocess.run(
            [self.executable, "cp", f"{self.container_id}:{container_path}", str(tmp_path)],
            capture_output=True,
            text=True,
            timeout=DOCKER_CP_TIMEOUT,
        )
        if result.returncode != 0:
            tmp_path.unlink(missing_ok=True)
            raise RuntimeError(_format_subprocess_failure(f"copy out {container_path}", result))
        tmp_path.replace(local_path)

    def copy_out_dir(
        self,
        container_path: str,
        local_path: Path,
        *,
        excludes: list[str] | None = None,
        members: list[str] | None = None,
    ) -> None:
        """Replace a local directory with a tar-streamed container directory."""
        if members is not None and any(not name or name in {".", ".."} or "/" in name or "\\" in name for name in members):
            raise ValueError("copy_out_dir members must be immediate children")
        tmp_path = local_path.with_name(f".{local_path.name}.tmp-{uuid.uuid4().hex}")
        shutil.rmtree(tmp_path, ignore_errors=True)
        tmp_path.mkdir(parents=True, exist_ok=True)
        producer = subprocess.Popen(
            [
                self.executable,
                "exec",
                self.container_id,
                "tar",
                "--no-same-owner",
                "--sparse",
                "-C",
                container_path,
                *(f"--exclude={pattern}" for pattern in (excludes or [])),
                "-cf",
                "-",
                "--",
                *(members if members is not None else ["."]),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        assert producer.stdout is not None
        try:
            extract = subprocess.run(
                ["tar", "--no-same-owner", "-xf", "-", "-C", str(tmp_path)],
                stdin=producer.stdout,
                capture_output=True,
                text=False,
                timeout=DOCKER_CP_TIMEOUT,
            )
        finally:
            producer.stdout.close()
            producer_stderr = producer.stderr.read().decode(errors="replace") if producer.stderr else ""
            producer_returncode = producer.wait()
        warned_only = producer_returncode == 1 and bool(producer_stderr.strip()) and all(
            _TAR_CHANGED_WARNING in line for line in producer_stderr.splitlines() if line.strip()
        )
        if (producer_returncode != 0 and not warned_only) or extract.returncode != 0:
            shutil.rmtree(tmp_path, ignore_errors=True)
            extract_stderr = extract.stderr.decode(errors="replace").strip()
            raise RuntimeError(
                f"copy out of container failed (docker rc={producer_returncode}, tar rc={extract.returncode}): "
                f"docker stderr={producer_stderr.strip()!r}; tar stderr={extract_stderr!r}"
            )
        if warned_only:
            log.warning(
                "Tolerating tar warning while copying %s out of container: %s",
                container_path, producer_stderr.strip(),
            )
        shutil.rmtree(local_path, ignore_errors=True)
        tmp_path.replace(local_path)

    def _stream_tar_in(
        self,
        container_path: str,
        *,
        producer: list[str] | None = None,
        stdin_stream=None,
        compressed: bool = False,
    ) -> None:
        """Pipe a tar stream into ``docker exec -i <c> tar --no-same-owner -xf - -C <dest>``.

        Either ``producer`` (a command spawned with stdout=PIPE) or
        ``stdin_stream`` (an open file-like) provides the tar bytes. Bypasses
        ``docker cp``'s symlink validation by letting the container's tar
        unpack the stream itself. Set ``compressed=True`` for gzip input.
        ``--no-same-owner`` keeps rootless Docker from trying to restore
        unmapped host uid/gid values.
        """
        mk = subprocess.run(
            [self.executable, "exec", self.container_id, "mkdir", "-p", container_path],
            capture_output=True,
            text=True,
            timeout=DOCKER_CP_TIMEOUT,
        )
        if mk.returncode != 0:
            raise RuntimeError(_format_subprocess_failure(f"mkdir -p {container_path} in container", mk))

        tar_flags = "-xzf" if compressed else "-xf"
        cmd = [self.executable, "exec", "-i", self.container_id, "tar", "--no-same-owner", "-C", container_path, tar_flags, "-"]
        if producer is not None:
            tar = subprocess.Popen(producer, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            try:
                cp = subprocess.run(cmd, stdin=tar.stdout, capture_output=True, text=True, timeout=DOCKER_CP_TIMEOUT)
            finally:
                tar.stdout.close()
                tar_rc = tar.wait()
                tar_err = tar.stderr.read().decode(errors="replace") if tar.stderr else ""
            if tar_rc != 0 or cp.returncode != 0:
                raise RuntimeError(
                    f"tar stream into container failed (producer rc={tar_rc}, exec rc={cp.returncode}): "
                    f"producer stderr={tar_err.strip()!r}; exec stdout={(cp.stdout or '').strip()!r}; "
                    f"exec stderr={(cp.stderr or '').strip()!r}"
                )
        else:
            cp = subprocess.run(cmd, stdin=stdin_stream, capture_output=True, text=True, timeout=DOCKER_CP_TIMEOUT)
            if cp.returncode != 0:
                raise RuntimeError(_format_subprocess_failure("tar stream into container", cp))

    def commit(self, image_ref: str) -> str:
        """Commit the current container state to a new image and return its ref."""
        cmd = [self.executable, "commit", self.container_id, image_ref]
        log.debug("Committing container: %s", " ".join(cmd))
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=DOCKER_RUN_TIMEOUT)
        if result.returncode != 0:
            raise RuntimeError(f"docker commit failed: {result.stderr.strip()}")
        return image_ref

    def cleanup(self) -> None:
        """Stop and remove the container."""
        container_id = getattr(self, "container_id", "")
        if not container_id:
            return
        if remove_container(self.executable, container_id):
            self.container_id = ""
        # Retain the ID after failure so a later cleanup/destructor can retry.

    def __del__(self) -> None:
        try:
            self.cleanup()
        except Exception:
            # Destruction may run during interpreter shutdown; explicit cleanup
            # reports Docker errors and retains the ID for retry.
            pass


def remove_image(image_ref: str, *, executable: str = "docker") -> None:
    """Best-effort image removal."""
    try:
        subprocess.run(
            [executable, "rmi", "-f", image_ref],
            capture_output=True,
            timeout=60,
        )
    except Exception:
        pass


def ensure_cleanroom_codex_image(instance_id: str) -> str:
    """The task's Codex cleanroom image, built by the installer when it is not present locally."""
    image = cleanroom_codex_image(instance_id)
    if subprocess.run([DOCKER_EXECUTABLE, "image", "inspect", image], capture_output=True).returncode:
        log.info("Cleanroom image %s is missing; building it", image)
        subprocess.run(
            [REPO_ROOT / "scripts" / "docker" / "install_codex_cleanroom.sh", "--task", instance_id],
            cwd=REPO_ROOT,
            check=True,
        )
    return image
