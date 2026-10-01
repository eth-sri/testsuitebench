#!/usr/bin/env bash
set -euo pipefail
# run.sh apt-installs zip for the archive tests when it is missing. Offline that
# aborts run.sh under `set -e` before pytest starts and the whole branch is
# recorded as not_run.
apt-get update
apt-get install -y --no-install-recommends zip
rm -rf /var/lib/apt/lists/*
