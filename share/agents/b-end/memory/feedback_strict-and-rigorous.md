---
name: strict-and-rigorous
description: User rule (2026-10-20) — be strict and rigorous with type checks, linting and formatting; clean, readable, idiomatic Python; fix data to fit strict types, never loosen the type
metadata:
  type: feedback
---

# Strict and rigorous

Be strict and rigorous with type checks, linting and formatting, so the code is clean, readable, and robust idiomatic Python.

**Why:** the user said so directly (2026-10-20, PR #23). In the same PR they chose pydantic `strict=True` on
`DomainModel` (review comment r4307551988) and had the test data fixed to the correct types. They turned down the
reviewer's alternative, `Field(strict=False)` on `recurring_outflow_ids`.

**How to apply:**

- When a strict setting breaks callers, fix the callers (test data, factories, fixtures) to pass correctly typed
  values. Don't relax the setting for one field or path. If production code breaks, report it instead of loosening.
- Tests should assert exactly what failed (`excinfo.value.errors()` types and `loc`), not a loose `match=` on the
  message. A loose match can hide a second, unrelated error.
- The gate is all of ruff check, ruff format, mypy, pyright and ty (see [[type-checkers]]), plus pytest with doctests.
  Each must report zero findings, with no blanket suppressions.
- Prefer the strictest reasonable option when a tool or library offers a choice, and write it down in config
  (see [[explicit-over-implicit]]).

Related: [[type-checkers]], [[explicit-over-implicit]].
