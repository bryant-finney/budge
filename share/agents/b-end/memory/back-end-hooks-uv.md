---
name: back-end-hooks-uv
description: back-end pre-commit hooks are `language: python` + pinned uv running `uv run -q --locked`, so CI can run them; pre-commit's VIRTUAL_ENV makes uv warn
metadata:
  type: feedback
---

# Back-end hooks run through pinned uv

CI runs every pre-commit hook ([[ci-runs-every-hook]]), so the back-end hooks can't rely on uv being on PATH.

**How to apply:**

- The back-end hooks are `language: python` with `additional_dependencies: [uv==<x.y.z>]` and `entry: uv run -q --locked ...`.
  pre-commit installs uv, and `uv run` creates and syncs `src/back-end/.venv` from `uv.lock` on its own (checked in a
  depth-1, tagless clone with uv off PATH). Versions stay in `uv.lock`, and the type checkers see the project's deps.
  Don't switch to mirror repos or a plain `additional_dependencies` list of runtime deps.
- Keep the `uv==` pin inside `[tool.uv] required-version`. Dependabot doesn't cover pre-commit, so bump it by hand.
- pre-commit sets `VIRTUAL_ENV` to the hook env, so `uv run` warns that it doesn't match the project `.venv`. `-q` hides
  that warning and uv's sync output, but still prints errors (a stale lock under `--locked`, for example).
- File-taking `uv run` hooks need `require_serial: true`, or pre-commit starts one `uv run` per file batch in parallel.
- A shallow, tagless checkout builds the editable package as `0.0.1.dev1+<sha>`, so a lint-only job doesn't need
  `fetch-depth: 0`. See [[uv-dynamic-versioning-quirks]].
