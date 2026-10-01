# Per-task evaluation dependencies

Python packages a single reference suite's `eval/run.sh` installs at runtime and
that cannot go in `scripts/docker/eval-runtime-requirements.txt`, because they need
system libraries or a build toolchain the 200 upstream base images do not all
carry. A hard `pip install -r` of one of these fails the layer, and with it the
image, for every task that cannot build it.

These are **not** withheld from the agent. Unlike `scripts/docker/mutant_build_deps/`,
which exists so the agent is not told what the implementation is built on, these
are part of the runtime an agent may legitimately write tests and code against.

What must hold instead is parity: solve, test generation and eval have to see the
same set. The hook in `programbench_image.Dockerfile` therefore runs in every
variant rather than behind the `AGENT` case, and all three builders --
`install_codex_cleanroom.sh`, `install_claude_cleanroom.sh` and
`install_task_patched.sh` -- pass the same `TASK`. A submission can then never
meet a package at grading time that it did not have while being written, nor
lose one it was written against.

Name each script `<instance_id>.sh`; it runs only when that file exists. Install
the system libraries it needs as well as the package itself, and keep it
idempotent -- the grading image is built from the cleanroom, so it may run twice.
