ARG BASE_IMAGE
FROM ${BASE_IMAGE}

# The one image every ProgramBench step runs in, except mutant/reference builds.
#
# Solve, test generation and eval must agree on the runtime or a submission can
# build under the agent and fail under the grader for reasons that have nothing
# to do with the implementation. Keeping them in one Dockerfile makes that
# agreement structural rather than a pair of files someone remembers to edit
# together. AGENT selects the only thing that legitimately differs.
#
# Everything below is identical in every task image, so it reveals nothing about
# the task under test. Task-specific dependencies belong in
# task_mutantbuild.Dockerfile, which no agent ever runs in.

ARG AGENT=none

# curl and ca-certificates are needed by the sccache and Claude installs below;
# git and util-linux are part of the baseline agent workspace.
RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates curl git gnupg util-linux \
  && rm -rf /var/lib/apt/lists/*

# Concurrent builds otherwise race on the dpkg lock.
COPY scripts/docker/apt-flock-wrapper.sh /usr/local/libexec/programbench-apt-flock
RUN chmod 0755 /usr/local/libexec/programbench-apt-flock \
  && ln -sf /usr/local/libexec/programbench-apt-flock /usr/local/bin/apt \
  && ln -sf /usr/local/libexec/programbench-apt-flock /usr/local/bin/apt-get

# sccache lets the 300+ locked dependencies shared by every mutant compile once
# instead of once per mutant. It is a generic build tool, identical in every
# image, so it reveals nothing about the task; the cache itself lives on the
# host and is mounted only into build containers.
ARG SCCACHE_VERSION=0.10.0
RUN curl -fsSL "https://github.com/mozilla/sccache/releases/download/v${SCCACHE_VERSION}/sccache-v${SCCACHE_VERSION}-x86_64-unknown-linux-musl.tar.gz" \
      | tar -xz -C /tmp \
  && install -m 0755 "/tmp/sccache-v${SCCACHE_VERSION}-x86_64-unknown-linux-musl/sccache" /usr/local/bin/sccache \
  && rm -rf "/tmp/sccache-v${SCCACHE_VERSION}-x86_64-unknown-linux-musl" \
  && sccache --version

# Node runtime, in every image including the grader. The agent has node while it
# works, so a submission may legitimately build or run with it; a grader without
# it would fail builds that succeeded under solve. Everything the agent CLI's
# install pulls in is therefore shared, and only the CLI itself is withheld.
ARG NODE_MAJOR=24
RUN install -d -m 0755 /etc/apt/keyrings \
  && curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key \
       | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg \
  && echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_${NODE_MAJOR}.x nodistro main" \
       > /etc/apt/sources.list.d/nodesource.list \
  && apt-get update \
  && apt-get install -y --no-install-recommends nodejs \
  && rm -rf /var/lib/apt/lists/* \
  && node --version
# Agent CLI. Deliberately absent from the grading image (AGENT=none): a
# submitted compile.sh that can invoke an agent could write the implementation
# at grading time. Muse is never installed here at all -- its binary is behind
# an authenticated download, so scripts/agents/solve_agent.py bind-mounts the
# host copy into the Muse agent image at run time.
#
# All are pinned. An unpinned installer would mean two rebuilds a month apart
# produce two different graders, which for a benchmark is a reproducibility hole.
ARG CODEX_VERSION=0.160.0
ARG CLAUDE_VERSION=2.1.280
ARG GEMINI_VERSION=0.60.0
ARG QWEN_VERSION=0.24.0
ARG DEEPSEEK_VERSION=0.1.5-rc.3
ARG ZCODE_VERSION=3.14.3
ARG MUSE_ADAPTER_VERSION=0.3.2
RUN set -eu; \
    case "${AGENT}" in \
      codex) \
        npm install -g "@openai/codex@${CODEX_VERSION}"; \
        npm cache clean --force >/dev/null 2>&1; rm -rf /root/.npm; \
        codex --version; \
        ;; \
      claude) \
        curl -fsSL https://claude.ai/install.sh | bash -s "${CLAUDE_VERSION}"; \
        /root/.local/bin/claude --version; \
        ;; \
      gemini) \
        npm install -g "@google/gemini-cli@${GEMINI_VERSION}"; \
        npm cache clean --force >/dev/null 2>&1; rm -rf /root/.npm; \
        gemini --version; \
        ;; \
      qwen) \
        npm install -g "@qwen-code/qwen-code@${QWEN_VERSION}"; \
        npm cache clean --force >/dev/null 2>&1; rm -rf /root/.npm; \
        qwen --version; \
        ;; \
      deepseek) \
        npm install -g "@deepseek-ai/dsh@${DEEPSEEK_VERSION}"; \
        npm cache clean --force >/dev/null 2>&1; rm -rf /root/.npm; \
        dsh --version; \
        ;; \
      glm) \
        curl -fsSL "https://cdn-zcode.z.ai/zcode/electron/releases/${ZCODE_VERSION}/linux-x64/ZCode-${ZCODE_VERSION}-linux-x64.deb" -o /tmp/zcode.deb; \
        mkdir -p /opt/zcode; \
        dpkg-deb -x /tmp/zcode.deb /opt/zcode; \
        rm /tmp/zcode.deb; \
        test -f /opt/zcode/opt/ZCode/resources/glm/zcode.cjs; \
        ln -s ../config/provider /opt/zcode/opt/ZCode/resources/glm/provider; \
        printf '#!/bin/sh\nexec node /opt/zcode/opt/ZCode/resources/glm/zcode.cjs "$@"\n' > /usr/local/bin/zcode; \
        chmod 0755 /usr/local/bin/zcode; \
        zcode --version; \
        printf '%s\n' "${ZCODE_VERSION}" > /opt/programbench-zcode-version; \
        ;; \
      muse) \
        python3 -m pip install --no-cache-dir "muse-code-openrouter==${MUSE_ADAPTER_VERSION}"; \
        python3 -c "import muse_code_openrouter; print(muse_code_openrouter.__version__)"; \
        ;; \
      none) : ;; \
      *) echo "AGENT must be one of: none, codex, claude, gemini, qwen, deepseek, glm, muse (got: ${AGENT})" >&2; exit 1 ;; \
    esac

# Python test runtime. Preinstalled so eval/run.sh scripts, which are
# model-authored and install their dependencies at runtime, keep working with
# networking disabled: pip exits 0 when everything requested is already
# satisfied. The constraint bounds whatever they still try to resolve.
#
# Deliberately below the agent CLI. This layer and the one after it change
# whenever a reference suite turns out to need another package, and Docker
# invalidates everything below a changed layer. Above the CLI install, each edit
# to the package list cost a full nodejs and agent reinstall per image -- about
# five minutes each, across 200 tasks -- to redo a pip layer that takes twenty
# seconds.
COPY scripts/docker/pip-constraints.txt /opt/programbench/constraints.txt
ENV PIP_CONSTRAINT=/opt/programbench/constraints.txt
COPY scripts/docker/eval-runtime-requirements.txt /opt/programbench/requirements.txt
RUN python3 -m pip install -q -r /opt/programbench/requirements.txt

# Python packages a single reference suite installs that need system libraries or
# a build toolchain, which is why they cannot join the flat `pip install -r`
# above: that would fail the layer, and the image, for every task whose base
# image cannot build them.
#
# Unlike task_mutantbuild.Dockerfile's build dependencies these are NOT withheld
# from the agent. They are part of the runtime it may write tests and code
# against, so the only thing that matters is that solve, test generation and eval
# see exactly the same set. That is why this runs in every variant rather than
# behind the AGENT case: every builder passes the same TASK and therefore gets
# the same packages, and a submission can never meet a package at grading time
# that it did not have while being written.
ARG TASK=
COPY scripts/docker/eval_deps /tmp/programbench-eval-deps
RUN if [ -n "${TASK}" ] && [ -f "/tmp/programbench-eval-deps/${TASK}.sh" ]; then \
        bash "/tmp/programbench-eval-deps/${TASK}.sh"; \
    fi \
 && rm -rf /tmp/programbench-eval-deps

# Set unconditionally: harmless where the CLI is absent, and keeping the
# environment identical across variants is the point of this file.
ENV CODEX_HOME=/root/.codex
ENV CLAUDE_CONFIG_DIR=/tmp/programbench-claude-config
ENV PATH=/root/.local/bin:${PATH}
ENV NPM_CONFIG_UPDATE_NOTIFIER=false
ENV NO_UPDATE_NOTIFIER=1
ENV DISABLE_AUTOUPDATER=1
ENV DISABLE_TELEMETRY=1
ENV IS_SANDBOX=1
RUN mkdir -p /root/.codex /tmp/programbench-claude-config
