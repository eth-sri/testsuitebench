#!/usr/bin/env bash
set -euo pipefail
# The reference suite's run.sh builds age-keygen and age-plugin-batchpass from the
# branch checkout with `go build`. The branch's go.mod pins `toolchain go1.25.5`,
# so offline the very first `go` call dies downloading that toolchain and neither
# suite branch writes results.xml (462 tests recorded as not_run). Fetching the
# toolchain and the module graph here caches them under /root/go/pkg/mod, where
# the eval container finds them with no network. The prefetch module mirrors the
# branch go.mod exactly; only third-party modules land in the cache, never the
# reference source. Idempotent: cached downloads are no-ops.
GOTOOLCHAIN=go1.25.5 go version
prefetch=$(mktemp -d)
cat > "${prefetch}/go.mod" <<'EOF'
module prefetch

go 1.24.0

toolchain go1.25.5

require (
	filippo.io/edwards25519 v1.1.0
	filippo.io/hpke v0.4.0
	filippo.io/nistec v0.0.4
	golang.org/x/crypto v0.45.0
	golang.org/x/sys v0.38.0
	golang.org/x/term v0.37.0
)

require (
	c2sp.org/CCTV/age v0.0.0-20251208015420-e9274a7bdbfd
	github.com/rogpeppe/go-internal v1.14.1
	golang.org/x/tools v0.39.0 // indirect
)
EOF
(cd "${prefetch}" && GOTOOLCHAIN=go1.25.5 go mod download all)
rm -rf "${prefetch}"
