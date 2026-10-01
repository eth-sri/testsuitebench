#!/usr/bin/env bash
set -euo pipefail
# The reference suite installs these unguarded under `set -e`, so offline they
# abort run.sh before it writes results.xml and the whole branch is recorded as
# errors. Both pull in cairo/pango and qpdf shared libraries.
apt-get update
apt-get install -y --no-install-recommends \
    libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf-2.0-0 libffi-dev shared-mime-info
rm -rf /var/lib/apt/lists/*
python3 -m pip install -q weasyprint pypdf
