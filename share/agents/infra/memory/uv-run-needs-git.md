---
name: uv-run-needs-git
description: In the dev container, `uv run` without Git passes tests but writes version 0.0.0 to the checkout's budge/_version.py; keep the read-only Git common-dir mount on api
metadata:
  type: project
---

# `uv run` in the dev container needs the Git mount

On 2026-11-03, removing the read-only Git common-dir mount from `api` looked safe: uvicorn ran, and
`uv run --frozen pytest` still passed 216 tests. But the image sets `UV_NO_INSTALLER_METADATA=1`, so
`uv run` rebuilds the editable install every time. In a linked worktree without the mount, Git can't
resolve, `uv-dynamic-versioning` uses its `0.0.0` fallback without an error, and the build hook writes
that to `budge/_version.py` on the host. Plain `pytest` then fails 4 version tests until the next good
rebuild. `git` in the container fails outright.

**How to apply:** keep the mount in `etc/compose/targets/dev.yaml`. When a mount or environment
change could affect the version, check the contents of `budge/_version.py` after `uv run`, and test from a
clean host state, because a passing test run doesn't show this. Host `uv sync` restores the file.

Unexplained: one `uv run --frozen pytest` from a fresh plain clone, with Git available, also wrote `0.0.0`
that day. Eleven later `uv run` calls, five of them from fresh clones in the same sequence, wrote the right
version, so the cause is unknown. If it recurs, capture `uv run -v` output before rerunning.
