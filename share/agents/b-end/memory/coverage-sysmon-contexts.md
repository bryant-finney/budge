---
name: coverage-sysmon-contexts
description: coverage >= 7.16 on Python >= 3.14 picks the sysmon core, which breaks --cov-context=test under filterwarnings=error; pin core = "ctrace"
metadata:
  type: feedback
---

# coverage: sysmon core vs. per-test contexts

Keep `[tool.coverage.run] core = "ctrace"` in `src/back-end/pyproject.toml` while pytest runs with
`--cov-context=test` and `filterwarnings = ["error"]`.

**Why:** coverage 7.16 defaults to the `sys.monitoring` ("sysmon") core on Python 3.14+. pytest-cov switches
dynamic contexts at runtime (`Coverage.switch_context`), after the core is chosen, and sysmon can't record them, so
coverage emits `CoverageWarning ... (no-sysmon-context)`. `filterwarnings = error` turns that into one error per test
on the 3.14 and 3.15 legs only. 3.11-3.13 were green, so a single-version local run hides it (found on #1 /
PR #19, 2026-10-17).

**How to apply:** always run the full 3.11-3.15 matrix before calling back-end test config done; a green
default-interpreter run is not evidence. Drop the pin only once coverage supports dynamic contexts under sysmon
(check `coverage/core.py` `reason_no_sysmon`). Related: [[local-python-matrix]].
