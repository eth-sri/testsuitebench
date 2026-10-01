#!/usr/bin/env bash
set -euo pipefail
# Installed unguarded under `set -e` by the reference suite. pikepdf binds qpdf.
apt-get update
apt-get install -y --no-install-recommends libqpdf-dev
rm -rf /var/lib/apt/lists/*
python3 -m pip install -q pikepdf
