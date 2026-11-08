---
name: dev-image-no-uv-or-git
description: Owner decision on PR 34 - the dev image has no uv or Git at runtime and its install's metadata reports 0.0.0, because uv-dynamic-versioning runs on the host
metadata:
  type: project
---

# The dev image has no uv or Git

Decided by the owner on PR #34, 2026-11-03: "it's okay for the `dev` image's editable install to ignore `git` and
fallback to `0.0.0`. `uv-dynamic-versioning` should run from the host instead of the container", and "`uv` should only
be available to the `build` and dependency installation layers. this sounds like a test issue more than anything
else".

**Why:** the version belongs to the host's `.envrc`. With uv and Git in the container, a `uv run` could rebuild the
editable install and write a wrong version to the host's `budge/_version.py` through the source mount. Without uv, nothing
in the container can.

**How to apply:**

- `etc/compose/targets/dev.yaml` has no Git mounts, and `dev`'s only uv use is a `RUN --mount=from=uv` layer.
- `budge.__version__` is still the host's, from `budge/_version.py`. See [[version-source-of-truth]].
- Run tools directly in the container: `docker compose run --rm api pytest`, not `uv run`.
- `dev`'s metadata saying `0.0.0` isn't a bug, so don't check it against the host. See [[compose-layering]] for how the
  mount sources resolve.
