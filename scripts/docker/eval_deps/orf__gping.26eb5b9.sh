#!/usr/bin/env bash
set -euo pipefail
# run.sh apt-installs iputils-ping unguarded under `set -e`; offline that aborts
# before pytest starts and the whole branch is recorded as not_run. Most of the
# suite pings localhost, so the tests themselves run without a network.
apt-get update
apt-get install -y --no-install-recommends iputils-ping
rm -rf /var/lib/apt/lists/*
