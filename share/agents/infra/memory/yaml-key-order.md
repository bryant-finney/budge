---
name: yaml-key-order
description: Sort YAML object keys alphabetically; in GitHub Actions workflows put top-level name, on, permissions first, in that order
metadata:
  type: feedback
---

# YAML key order

Sort YAML object keys alphabetically at every level. GitHub Actions workflows are the exception
at the top level: `name`, `on` and `permissions` come first, in that order, followed by the
remaining top-level keys sorted (for example `concurrency`, `env`, `jobs`). Lists keep their
order: steps, `needs`, `matrix.include`, trigger lists and the like.

**Why:** On PR #32 (2026-10-28) the user asked for sorted keys in `.github/workflows/ci.yml`, then
added the workflow exception so a reader sees what the workflow is, when it runs and what it may
do before anything else.

**How to apply:**

- When writing or editing any YAML, sort mapping keys alphabetically; never reorder sequences.
- In `.github/workflows/*.yml`, lead with `name`, `on`, `permissions`; everything else, including
  every nested mapping (jobs, steps' `with`, `env`), stays alphabetical.
- Check a reorder with PyYAML `BaseLoader` against `HEAD` (`safe_load` parses `on` as `true`),
  then run `actionlint`.
- Keep any header comment describing the order to one line ([[comments-sparingly]]).
