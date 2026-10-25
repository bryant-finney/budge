---
name: ruff-over-pylint
description: User rule (2026-10-25) — ruff owns every check it has a rule for and pylint keeps only the rest; the chosen exceptions, how to re-derive the split, and how to run pylint
metadata:
  type: feedback
---

# ruff over pylint

For each default pylint message, the check runs in exactly one tool:

1. **ruff has a counterpart rule:** ruff owns it. Select the rule in `[tool.ruff.lint]`, put its options in ruff's
   config (e.g. thresholds in `[tool.ruff.lint.pylint]`), and disable the pylint message with a comment naming the ruff
   code. This applies even when the ruff rule is preview-only or in a family not otherwise selected.
2. **No ruff counterpart:** keep pylint's default. Never disable a pylint message that has no matching ruff rule.

pylint options that mirror ruff values are not kept. The exception is interpreter config pylint needs, such as
`py-version`, which tracks ruff's `target-version`.

**Why:** the user wants ruff used wherever it supports a check and pylint kept only for what ruff can't do. They
rejected an earlier rule that kept pylint checks on with mirrored ruff values when the ruff rule wasn't enabled.

**Exceptions the user chose:**

- pylint's naming checks stay on beside pep8-naming (`invalid-name`, `bad-classmethod-argument`,
  `no-self-argument`, `non-ascii-file-name`) because they also cover constants and TypeVars. This is the one
  deliberate overlap with rule 1. `[tool.pylint.basic]` styles match pep8-naming wherever both apply.
- No camelCase allowances: `good-names` keeps only short names, not pep8-naming's `ignore-names` (`setUp`, `maxDiff`,
  ...).
- `redefined-outer-name` (no ruff counterpart) is off in `tests/` only, through the `pylint-per-file-ignores` plugin.
  pytest injects fixtures by parameter name, so tests always shadow them; the check stays on for `budge/`. pylint 4
  has no per-directory or per-file message control of its own. The plugin's globs are resolved relative to pylint's
  cwd (a leading `/` matches nothing), hence the paired `tests/**` and `src/back-end/tests/**` patterns.

**How to apply:**

- **Formatter-owned checks:** when the ruff counterpart conflicts with `ruff format` (E111, Q000 and others), don't
  select it; `ruff format --check` warns about those. Disable the pylint message and comment that `ruff format` owns
  the check.
- **Preview rules:** enable them only by exact code under `[tool.ruff.lint]` with `preview = true` and
  `explicit-preview-rules = true`. Use lint-level `preview`, never top-level `[tool.ruff] preview`, which would also
  switch the formatter to preview style.
- **Re-deriving the split** whenever ruff, pylint or ruff's `select` changes:
  1. List pylint's default messages: `uv run pylint --list-msgs-enabled`.
  2. Map each one to ruff. `PLxxxx` maps to pylint `xxxx` directly. For other rules, use the astral-sh/ruff#970 body
     (`gh issue view 970 --repo astral-sh/ruff`). It lags ruff: some rules were renamed (TRY302 is now TRY203) or
     removed (PLR1701, PLR1706), so check each code's `status` in `uv run ruff rule --all --output-format json`.
     A removed rule means the message has no counterpart.
  3. Disable a pylint message only if it's on that default list. Unloaded extension messages raise
     `unknown-option-value` (W0012).
  4. Confirm the active preview rules are exactly the intended ones: compare `linter.rules.enabled` from
     `uv run ruff check --show-settings <file>` against the preview rules. Check `tests/` too, whose `ruff.toml`
     extends the project config.
- **Running pylint:** `uv run pylint budge tests` from `src/back-end`. pylint and the plugin are in the dev group, and
  pylint reads `[tool.pylint]` only from its cwd or from `--rcfile src/back-end/pyproject.toml`.
- **Verifying:** pylint (no W0012/E0015), `ruff check`, `ruff format --check` (no incompatibility warnings), and
  pre-commit (`taplo-format` realigns inline comments).

Related: [[strict-and-rigorous]], [[explicit-over-implicit]].
