#!/bin/sh
set -eu

# apt and apt-get share dpkg state, so parallel invocations in one task
# container must be serialized. This file is exposed through symlinks named
# apt and apt-get in /usr/local/bin.
command_name=${0##*/}
case "$command_name" in
    apt|apt-get) ;;
    *)
        echo "programbench apt wrapper must be invoked as apt or apt-get" >&2
        exit 64
        ;;
esac

lock_file=${PROGRAMBENCH_APT_LOCK_FILE:-/var/lock/programbench-apt.lock}
apt_bin_dir=${PROGRAMBENCH_APT_BIN_DIR:-/usr/bin}

exec /usr/bin/flock -x "$lock_file" "$apt_bin_dir/$command_name" "$@"
