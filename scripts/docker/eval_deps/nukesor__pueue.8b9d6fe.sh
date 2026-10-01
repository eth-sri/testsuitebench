#!/usr/bin/env bash
set -euo pipefail
# The reference suite's run.sh builds the pueued daemon from the branch checkout
# with `cargo build --release --bin pueued`. Offline, cargo cannot reach
# index.crates.io and the branch aborts before pytest starts (371 tests recorded
# as not_run). `cargo fetch --locked` against the pinned upstream lockfile fills
# /root/.cargo/registry with every crate and index entry the build needs, so the
# eval container resolves entirely from the cache. Only third-party crates are
# cached; the clone is removed and workspace members are path dependencies that
# cargo never downloads. Idempotent: cached crates are no-ops.
src=$(mktemp -d)
git clone --quiet https://github.com/Nukesor/pueue "${src}"
git -C "${src}" checkout --quiet 8b9d6fe
(cd "${src}" && cargo fetch --locked)
rm -rf "${src}"
