---
name: pyright-gotchas
description: pyright quirks in budge (contextmanager return type, HTTPStatus 422 name on 3.11, declared-object narrowing, nodenv, silent hang when pyright is missing from .venv, private-import from repo root) and __all__ enforcement
metadata:
  type: feedback
---

# pyright gotchas

- **`@contextlib.contextmanager` must return `Generator[T, None, None]`, not `Iterator[T]`.** pyright 1.1.414
  strict reports `reportDeprecated` for `-> Iterator[None]` (typeshed deprecates that overload). Use the
  three-argument `Generator` form, which also works on the 3.11 floor.

- **`HTTPStatus.UNPROCESSABLE_CONTENT` only exists from 3.13** (#29, 2026-10-27). The checkers target 3.11, so all
  three report it. Use `fastapi.status.HTTP_422_UNPROCESSABLE_CONTENT`. Starlette's `HTTP_422_UNPROCESSABLE_ENTITY` is
  deprecated.

- **A declared `x: object = y` still narrows to `y`'s type**, so a later `isinstance(x, str)` is
  `reportUnnecessaryIsInstance` (and mypy `redundant-expr`) when `y` is typed `str` but can hold anything at runtime
  (Starlette's `HTTPException.detail`). `x = cast('object', y)` doesn't narrow.

- **The PyPI `pyright` wrapper runs `node` from `PATH`.** The nodenv shim resolves the nearest `.node-version`
  walking up from the cwd. On 2026-10-17 that was a Node (`24.22.0`) that wasn't installed, and pyright died with
  `nodenv: version ... is not installed`. By 2026-10-20 the repo-root `.node-version` (`24.22.0`) is installed and
  `uv run pyright` works in the pr-23 worktree with no override. If a `.node-version` names an uninstalled Node again,
  run `NODENV_VERSION=system uv run pyright`; the pre-commit pyright hook (#5) will need the same Node.

- **pyright is a dev dependency, so `uv run pyright` resolves from `.venv` (2026-10-20).** Between #20's ty swap
  (`4c8e21d`) and its return in #23, pyright wasn't installed. `uv run pyright` then fell through to the pyenv shim,
  which re-enters `pyenv-which pyright` forever with no output. If `uv run pyright` hangs silently, the venv lacks
  pyright: run `uv sync --all-groups`. Wrap pyright runs in `timeout`.

- **`reportPrivateImportUsage` fires only from the repo root.** Pylance's workspace is the repo root, so `budge`
  resolves through the `.venv` editable `.pth` as an installed `py.typed` library. A bare `from x import y` in
  `budge/__init__.py` is then private, and `budge.y` is flagged. From `src/back-end` pyright treats `budge` as local
  source and stays silent. To check the whole layer from the worktree root with the locked pyright, run
  `src/back-end/.venv/bin/pyright --pythonpath src/back-end/.venv/bin/python src/back-end`. The user's
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
