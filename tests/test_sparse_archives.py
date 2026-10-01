"""Large sparse fixtures must stay sparse through packaging and container copies."""

import hashlib
import subprocess

import pytest

from programbench.container import ContainerEnvironment
from programbench.test_generation import _extract_test_suite


@pytest.fixture
def sparse_file(tmp_path):
    path = tmp_path / 'source' / 'fixture.bin'
    path.parent.mkdir()
    with path.open('wb') as stream:
        stream.write(b'header')
        stream.seek(8 * 1024 * 1024)
        stream.write(b'middle')
        stream.seek(16 * 1024 * 1024 - 4)
        stream.write(b'tail')
    if path.stat().st_blocks * 512 >= path.stat().st_size // 2:
        pytest.skip('filesystem does not support sparse files')
    return path


@pytest.fixture
def local_container(tmp_path):
    # Execute the real tar commands without a Docker daemon.
    docker = tmp_path / 'docker'
    docker.write_text("""#!/bin/sh
shift
if [ "$1" = -i ]; then shift; fi
shift
exec "$@"
""")
    docker.chmod(0o755)
    env = ContainerEnvironment.__new__(ContainerEnvironment)
    env.executable = str(docker)
    env.container_id = 'test-container'
    return env


def assert_sparse_copy(source, target):
    assert target.stat().st_size == source.stat().st_size
    assert hashlib.sha256(target.read_bytes()).digest() == hashlib.sha256(source.read_bytes()).digest()
    assert target.stat().st_blocks * 512 < target.stat().st_size // 8


@pytest.mark.parametrize('method', ['directory', 'file', 'many', 'out'])
def test_container_copies_preserve_holes(local_container, sparse_file, tmp_path, method):
    destination = tmp_path / 'destination'
    if method == 'directory':
        local_container.copy_in(sparse_file.parent, str(destination))
    elif method == 'file':
        local_container.copy_in(sparse_file, str(destination / sparse_file.name))
    elif method == 'many':
        local_container.copy_in_many(sparse_file.parent, [sparse_file.name], str(destination))
    else:
        local_container.copy_out_dir(str(sparse_file.parent), destination)
    assert_sparse_copy(sparse_file, destination / sparse_file.name)


def test_file_copy_follows_symlinks(local_container, tmp_path):
    blob = tmp_path / 'blobs' / 'abc'
    blob.parent.mkdir()
    blob.write_bytes(b'payload')
    link = tmp_path / 'snapshots' / 'executable'
    link.parent.mkdir()
    link.symlink_to(blob)
    destination = tmp_path / 'destination' / 'executable'
    local_container.copy_in(link, str(destination))
    assert not destination.is_symlink()
    assert destination.read_bytes() == b'payload'


def test_sparse_test_archive_preserves_holes_on_host_and_in_worker(
    local_container, sparse_file, tmp_path,
):
    workspace = tmp_path / 'workspace'
    eval_dir = workspace / 'eval'
    eval_dir.mkdir(parents=True)
    fixture = eval_dir / sparse_file.name
    sparse_file.rename(fixture)
    archive = tmp_path / 'tests.tar.gz'
    subprocess.run([
        'tar', '--sparse', '-czf', str(archive), '-C', str(workspace), 'eval',
    ], check=True)
    assert archive.stat().st_size < 64 * 1024
    unpacked = _extract_test_suite(archive)
    assert_sparse_copy(fixture, unpacked / 'eval' / fixture.name)
    destination = tmp_path / 'worker'
    local_container.copy_in_tar(archive, str(destination))
    assert_sparse_copy(fixture, destination / 'eval' / fixture.name)
