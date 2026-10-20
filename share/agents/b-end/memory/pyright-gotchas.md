---
name: pyright-gotchas
description: pyright quirks in budge (contextmanager return type, nodenv node lookup, reportPrivateImportUsage only from repo root) and what each checker does or does not enforce about __all__
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

- **`reportPrivateImportUsage` fires only from the repo root.** Pylance's workspace is the repo root, so `budge`
  resolves through the `.venv` editable `.pth` as an installed `py.typed` library. A bare `from x import y` in
  `budge/__init__.py` is then private, and `budge.y` is flagged. From `src/back-end` pyright treats `budge` as local
  source and stays silent. To check the whole layer from the worktree root, run
  `NODENV_VERSION=system uvx pyright --pythonpath src/back-end/.venv/bin/python src/back-end`. The user's
  convention (2026-10-20) is to list the name in the module's `__all__`, not to use an `import y as y` alias. See
  [[explicit-over-implicit]].

- **Checker coverage of `__all__` (2026-10-20).**

  - pyright and mypy use `__all__` only for imported names. A name the module defines itself (class, function,
    constant) stays public even when `__all__` leaves it out. No checker reports an incomplete `__all__`, so
    `tests/test_exports.py` enforces it (see [[explicit-over-implicit]]).
  - mypy's `no_implicit_reexport` (on via `strict`) flags a bare re-export, unless the module also declares the name
    (e.g. `__version__: str` before the import). `semanal.py` `process_import_over_existing_name` turns that import
    into an assignment to a public `Var`.
  - ty 0.0.89 applies re-export conventions only in `.pyi` stubs.
  - ruff's `__all__` rules (F822, PLE0604, PLE0605, RUF022, RUF068) are already on through `select`. They check the
    entries that are listed. None requires `__all__` or checks that it is complete; that is the test's job.

**How to apply:** when pyright fails before analysis, check `nodenv version` from `src/back-end` first. Don't edit
another layer's `.node-version` to work around it.
