---
name: version-source-of-truth
description: Owner design decision - budge.__version__ from the generated budge._version module is the version's source of truth, direnv sets BUDGE_VERSION and makes the hatch hook write _version.py, and there are no version build args
metadata:
  type: project
---

# Version source of truth

Decided by the owner on PR #34, 2026-11-03: "drop these build arguments; `direnv` should already set this variable and
write the `_version.py` file for programmatic access. the source of truth is the `budge` package's `__version__` variable
from the managed `budge._version` module". The owner asked for this design to be remembered.

**Why:** the version has one home, and Compose carries no version state into a build. Image builds have no Git, so the
host has to supply it.

**How to apply:**

- `.envrc` runs `uv-dynamic-versioning`, updates `BUDGE_VERSION` (the image tag, without the `+` local segment) in
  `.env`, and, when `src/back-end/budge/_version.py` is missing or doesn't hold that version, runs
  `hatch build --hooks-only` in `src/back-end` so the hatch hook (the file's only writer) rewrites it. The check greps
  for the hook template's `__version__` line, so change them together. `.dockerignore` must not exclude that file.
- The hatch hook rewrites `_version.py` on every build, and without Git it writes `0.0.0`. So deleting the build arg alone
  would lose the version. The `build` stage derives `UV_DYNAMIC_VERSIONING_BYPASS` inside its `RUN` from
  `import budge; print(budge.__version__)`, and `dev` copies the file again after its `uv sync`.
- `rel`: `budge.__version__` and `importlib.metadata` both equal the host's version. `dev`: `budge.__version__` is the
  host's, and metadata stays `0.0.0` by the decision in [[dev-image-no-uv-or-git]]. A real version there would fail
  `versions_agree` on the first commit after a build, because the mounted file moves and the image doesn't.
- Without `_version.py` (a fresh clone with no direnv, or `env -i` with no earlier run), both images build and report
  `0.0.0`, from the fallback in `budge/__init__.py`.
- A build reads whatever file is on the host, so a build before `.envrc` reruns gets the old version. `.env`'s image tag
  is equally old, so the tag and the version still agree.
