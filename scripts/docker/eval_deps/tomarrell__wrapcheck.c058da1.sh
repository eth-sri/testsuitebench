#!/usr/bin/env bash
set -euo pipefail
# The image ships go1.21.0 with GOTOOLCHAIN=auto and an empty module cache. The
# reference fixtures' go.mod asks for a newer Go, so every `go` invocation the tool
# makes tries to download that toolchain: offline the suite fails outright, and
# online the first tests race the download and time out. Fetching it here caches
# it under /root/go/pkg/mod, where the eval container finds it with no network.
# Idempotent: a cached toolchain is a no-op.
GOTOOLCHAIN=go1.24.0 go version
