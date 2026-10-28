---
name: ci-runs-every-hook
description: CI enforces every pre-commit hook and never SKIPs one; design hooks so a clean checkout with only pre-commit and CI's toolchain can run them
metadata:
  type: feedback
---

# CI runs every pre-commit hook

Pre-commit is the enforcement point: CI runs every hook and never `SKIP`s one. Design hooks so a
clean checkout with only pre-commit (plus the toolchain CI already sets up) can run them.

**Why:** on PR #30 (2026-10-27) b-end proposed that #32's CI skip the back-end hooks because they
were `language: system` and needed uv on PATH. The owner asked "why do the hooks need `uv`? CI
should enforce the `pre-commit` hooks, not skip them".

**How to apply:**

- When a hook needs a tool CI doesn't install, let pre-commit install it (`language: python` or
  `node` with `additional_dependencies`) rather than skipping the hook in CI.
- A hook that rewrites files must exit non-zero when it changes something, so CI fails on drift.
- Back-end specifics (pinned uv, `uv run -q --locked`): [[back-end-hooks-uv]].
