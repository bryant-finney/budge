---
name: pylint-mirrors-ruff
description: User rule (2026-10-25) for how `[tool.pylint]` relates to ruff, the chosen exceptions, how to re-derive the disable list, and how to run pylint
metadata:
  type: feedback
---

# pylint mirrors ruff

`[tool.pylint]` in `src/back-end/pyproject.toml` follows one rule for each default pylint message:

1. **ruff enforces the check** (its counterpart is in ruff's *enabled* set): disable it in pylint, with a comment
   naming the ruff code.
2. **ruff has a counterpart that isn't enabled** (not selected, or preview-only): keep it on in pylint, set to ruff's
   option value, with a comment naming the ruff setting.
3. **No ruff counterpart:** keep pylint's default. Never disable a pylint message that has no matching ruff rule.

**Why:** the user wants pylint, wherever it runs, to agree with ruff without reporting the same finding twice. They
corrected an early draft that disabled messages ruff doesn't cover.

**Exceptions the user chose:**

- Naming checks stay on in pylint beside pep8-naming (`invalid-name`, `bad-classmethod-argument`,
  `no-self-argument`, `non-ascii-file-name`). `[tool.pylint.basic]` styles match pep8-naming wherever both apply.
- No camelCase allowances: `good-names` keeps only short names, not pep8-naming's `ignore-names` (`setUp`, `maxDiff`,
  ...).
- `redefined-outer-name` is off in `tests/` only, through the `pylint-per-file-ignores` plugin. pytest injects
  fixtures by parameter name, so tests always shadow them; the check stays on for `budge/`. pylint 4 has no
  per-directory or per-file message control of its own. The plugin's globs are resolved relative to pylint's cwd (a
  leading `/` matches nothing), hence the paired `tests/**` and `src/back-end/tests/**` patterns.

**How to apply:**

- Run pylint with `uv run pylint budge tests` from `src/back-end`. pylint and the plugin are in the dev group. pylint
  reads `[tool.pylint]` only from its cwd, or from `--rcfile src/back-end/pyproject.toml`.
- Re-derive the disable list whenever ruff's `select`, ruff or pylint changes:
  1. Get ruff's enabled rules: `uv run ruff check --show-settings <file>` (`linter.rules.enabled`).
  2. Map `PLxxxx` to pylint `xxxx` directly. Map other ruff rules with the astral-sh/ruff#970 body
     (`gh issue view 970 --repo astral-sh/ruff`). It lags ruff, so trust ruff's `PL*` codes over its checkboxes.
  3. Keep only messages that `uv run pylint --list-msgs-enabled` reports as enabled. Unloaded extension messages
     raise `unknown-option-value` (W0012).
  4. Recheck the rule-2 option values against ruff's settings.
- Verify with pylint (no W0012/E0015), ruff check and format, and pre-commit (`taplo-format` realigns the inline
  comments).

Related: [[strict-and-rigorous]], [[explicit-over-implicit]].
