---
name: ruff-nested-config-first-party
description: a nested ruff.toml (tests/ruff.toml) becomes ruff's project root, so isort classifies budge as third-party there unless known-first-party is set
metadata:
  type: feedback
---

# ruff: nested config and first-party detection

Keep `[tool.ruff.lint.isort] known-first-party = ["budge"]` in `src/back-end/pyproject.toml`.

**Why:** with `tests/ruff.toml` (`extend = "../pyproject.toml"`), ruff resolves `src` relative to `tests/`, so
`import budge` sorts with third-party imports in tests and gives `I001`, while `budge/` files sort it as first-party.
Settings inherited via `extend` keep their absolute anchoring: the `budge/aws/**` `TID251` per-file ignore still
resolves to `src/back-end/budge/aws/**` (checked with `ruff check --show-settings tests/...`; #2, 2026-10-17).

**How to apply:** when adding another nested `ruff.toml`, confirm with `--show-settings` that
`linter.isort.known_modules` and `linter.per_file_ignores` are what you expect.
