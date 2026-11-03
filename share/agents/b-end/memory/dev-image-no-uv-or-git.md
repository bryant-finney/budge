---
name: dev-image-no-uv-or-git
description: Owner decision on PR 34 - the dev image has no uv or Git at runtime and its metadata says 0.0.0; the version tests accept 0.0.0 on either side, and the sdist and wheel tests skip without uv
metadata:
  type: project
---

# The dev image has no uv or Git

Decided by the owner on PR #34, 2026-11-03: "it's okay for the `dev` image's editable install to ignore `git` and
fallback to `0.0.0`. `uv-dynamic-versioning` should run from the host instead of the container", and "`uv` should only
be available to the `build` and dependency installation layers. this sounds like a test issue more than anything
else".

**Why:** `src/back-end` is mounted at `/var/task`, so a container-side rebuild would write the fallback to the host's
`budge/_version.py`. With no uv in the image, nothing rebuilds it. In the container, `importlib.metadata` says `0.0.0`
while `budge.__version__` comes from the host's file.

**How to apply:**

- `0.0.0` is a legitimate version. `versions_agree` in `tests/test_package.py` accepts it on either side, and two
  different real versions still fail. Keep that shape instead of asserting equality.
- `budge._version` can be missing in the container when the host never built, so that test skips only when the
  metadata is the fallback.
- `built_distributions` skips without `uv` on `PATH`; CI and the host still run the sdist and wheel tests.
- Host commands stay `uv run`. In the container, run tools directly.
- `rel` has no Git either. `.envrc` writes the host's version to `budge/_version.py`, both images copy that file, and
  `rel`'s build passes `budge.__version__` to its install as `UV_DYNAMIC_VERSIONING_BYPASS`. By the owner's decision,
  there are no version build args. Without the file, both images report `0.0.0`.
