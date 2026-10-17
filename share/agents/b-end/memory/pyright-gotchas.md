---
name: pyright-gotchas
description: pyright strict quirks hit in budge (contextmanager return type, the PyPI wrapper's node lookup under nodenv)
metadata:
  type: feedback
---

# pyright gotchas

- **`@contextlib.contextmanager` must return `Generator[T, None, None]`, not `Iterator[T]`.** pyright 1.1.414
  strict reports `reportDeprecated` for `-> Iterator[None]` (typeshed deprecates that overload). Use the
  three-argument `Generator` form, which also works on the 3.11 floor.
- **The PyPI `pyright` wrapper runs `node` from `PATH`.** In a worktree under the main checkout, the nodenv shim
  resolves the nearest `.node-version` walking up, which can be the main checkout's file (Node `24.22.0`, not
  installed on 2026-10-17), and pyright dies with `nodenv: version ... is not installed`. Run
  `NODENV_VERSION=system uv run pyright` locally. CI is unaffected, but if a repo-root `.node-version` lands in
  `main`, the pre-commit pyright hook (#5) needs that Node installed (or the same override).

**How to apply:** when pyright fails before analysis, check `nodenv version` from `src/back-end` first. Don't edit
another layer's `.node-version` to work around it.
