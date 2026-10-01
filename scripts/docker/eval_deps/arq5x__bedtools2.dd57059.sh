#!/usr/bin/env bash
set -euo pipefail
# Guarded by `|| true`, so the suite still runs without it -- but every test that
# imports pysam then fails and reaches the classifier looking behavioural.
# pysam builds htslib, which needs these.
apt-get update
apt-get install -y --no-install-recommends \
    libbz2-dev liblzma-dev libcurl4-openssl-dev libssl-dev zlib1g-dev
rm -rf /var/lib/apt/lists/*
python3 -m pip install -q pysam
