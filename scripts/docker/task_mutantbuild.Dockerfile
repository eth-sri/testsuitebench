ARG BASE_IMAGE
FROM ${BASE_IMAGE}

# Build-only image for mutant and reference builds. No agent ever runs here, so
# task-specific dependencies may be pre-installed without telling the agent what
# the implementation is built on. Never use this as a base for a cleanroom.
ARG TASK
COPY scripts/docker/mutant_build_deps /tmp/programbench-build-deps
RUN if [ -f "/tmp/programbench-build-deps/${TASK}.sh" ]; then \
        bash "/tmp/programbench-build-deps/${TASK}.sh"; \
    fi \
 && rm -rf /tmp/programbench-build-deps

# Older cached cleanrooms contain sccache 0.8, which rejects Rust path remapping.
ARG SCCACHE_VERSION=0.10.0
RUN curl -fsSL "https://github.com/mozilla/sccache/releases/download/v${SCCACHE_VERSION}/sccache-v${SCCACHE_VERSION}-x86_64-unknown-linux-musl.tar.gz" \
      | tar -xz -C /tmp \
 && install -m 0755 "/tmp/sccache-v${SCCACHE_VERSION}-x86_64-unknown-linux-musl/sccache" /usr/local/bin/sccache \
 && rm -rf "/tmp/sccache-v${SCCACHE_VERSION}-x86_64-unknown-linux-musl"
