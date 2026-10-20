---
name: type-checkers
description: the user wants mypy, pyright and Astral's ty all supported as back-end type checkers (2026-10-20); ty does not replace pyright
metadata:
  type: project
---

# mypy, pyright and ty all run

The back end runs three type checkers, each strict, over `budge` and `tests`: mypy, pyright and ty. On 2026-10-20 the
user asked to support pyright and ty both. That reversed `4c8e21d` ("replace Pyright with Astral ty", #20), which had
dropped pyright. pyright returned in #23 with the settings from `bf1f6d2` and `a00be20`, both in #20's history
(strict, `enableTypeIgnoreComments = false`, `reportUnnecessaryTypeIgnoreComment`). Two settings were added then:
`pythonPlatform = "Linux"`, from the PR #20 review nit, and `reportImplicitOverride`, to pair with mypy's
`explicit-override`.

**Why:** the user gave no reason in the request. Issue #2 had already decided on "pyright strict alongside mypy". ty is
still 0.0.x, and the checkers enforce different things (see [[pyright-gotchas]] on `__all__` and re-exports).

**How to apply:**

- A change is done only when `uv run mypy`, `uv run pyright` and `uv run ty check` all report zero errors.
- Never describe one checker as replacing another. When adding or upgrading one, configure all three in step (target
  version and platform, `include`, rule-specific ignores).
- Suppressions stay per checker: `# type: ignore[code]`, `# pyright: ignore[rule]`, `# ty: ignore[rule]`. Each checker
  ignores the others' comments (pyright and ty by config, mypy by default) and fails on stale ones of its own.
- `.pre-commit-config.yaml` has no hook for any of the three yet, and `.github/workflows/` doesn't exist (2026-10-20).
  When infra adds them, all three need to be wired in.

Related: [[explicit-over-implicit]], [[pyright-gotchas]].
