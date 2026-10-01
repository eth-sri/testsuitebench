#!/usr/bin/env bash
set -euo pipefail
# Guarded by `|| true`. mysqlclient compiles against the MySQL client library;
# PyMySQL and cryptography are pure-Python/wheel and ship in the shared list.
apt-get update
apt-get install -y --no-install-recommends default-libmysqlclient-dev build-essential pkg-config
rm -rf /var/lib/apt/lists/*
python3 -m pip install -q mysqlclient
