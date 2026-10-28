---
name: required-checks-aggregator
description: Require a single `ci-ok` aggregator job, never per-matrix contexts; skipped required checks count as passing on GitHub
metadata:
  type: feedback
---

# Required checks: one aggregator

Make the `ci-ok` aggregator job in `.github/workflows/ci.yml` the only required status check in
`rules.md`. Don't list per-job or per-matrix-entry contexts.

**Why:** b02caa0 (PR #32) dropped `ci-ok` and required `pre-commit` plus each
`test (python, 3.x)` context. The user had suggested dropping it, then saw the problem with the
matrix (2026-10-28). Matrix contexts are named per entry, so the required list has to follow every
matrix change. A renamed or retired entry leaves its required context pending forever.

**How to apply:** `ci-ok` uses `needs:` on every job, runs `if: always()`, and fails on any result
other than `success`, `skipped` included. GitHub counts a skipped required check as passing, so
`ci-ok` must never be skippable. Don't give it a `name:`, because that renames the context. When
adding a CI job, add it to `ci-ok`'s `needs` instead of touching `rules.md`.
