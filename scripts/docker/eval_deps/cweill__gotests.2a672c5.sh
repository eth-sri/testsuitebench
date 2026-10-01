#!/usr/bin/env bash
set -euo pipefail
# The image ships go1.21.0 with GOTOOLCHAIN=auto and an empty module cache. The
# reference fixtures' go.mod asks for a newer Go, so every `go` invocation the tool
# makes tries to download that toolchain: offline the suite fails outright, and
# online the first tests race the download and time out. Fetching it here caches
# it under /root/go/pkg/mod, where the eval container finds it with no network.
# Idempotent: a cached toolchain is a no-op.
# conftest.py additionally builds a normalize helper importing
# golang.org/x/tools/imports inside the branch module, so that module (and its
# two indirect deps) must be in the cache as well.
GOTOOLCHAIN=go1.24.5 go version
prefetch=$(mktemp -d)
printf 'module prefetch\n\ngo 1.24.0\n\ntoolchain go1.24.5\n\nrequire golang.org/x/tools v0.38.0\n' > "${prefetch}/go.mod"
(cd "${prefetch}" && go mod download all)
rm -rf "${prefetch}"
