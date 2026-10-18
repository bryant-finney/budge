---
name: uv-dynamic-versioning-quirks
description: uv-dynamic-versioning needs hatchling (not uv_build); fallback-version is for missing .git, not missing tags; cache-keys; full CI checkout; `__version__` via a gitignored hatch-generated `_version.py`
metadata:
  type: reference
---

# uv-dynamic-versioning quirks

Decided for issue #1 (2026-10-17): budge gets its version from git tags via `uv-dynamic-versioning` on `hatchling`.

- The plugin does not work with the `uv_build` backend (README, astral-sh/uv#14561), so the back end uses hatchling with `[tool.hatch.build.targets.wheel] packages = ["budge"]` for the flat layout.
- `fallback-version` applies only when `.git` is absent (Docker build context, Dependabot `uv lock`). With no tags, Dunamai already yields a `0.0.0`-based dev version.
- The default Dunamai pattern matches the repo-wide protected `v*` tags (`release-tags` ruleset in `share/skills/apply-repo-rules/rules.md`), so no `pattern-prefix` is needed while budge is the only Python package.
- Set `[tool.uv] cache-keys = [{ file = "pyproject.toml" }, { git = { commit = true, tags = true } }]`, or `uv sync` keeps a stale editable version.
- CI checkout needs `fetch-depth: 0` + `fetch-tags: true` (infra's side).
- Check the resolved version with `uvx uv-dynamic-versioning` from `src/back-end/`.
- uv-dynamic-versioning has no file substitution (unlike poetry-dynamic-versioning, which config-ninja uses).

## `budge.__version__` (decided 2026-10-17, PR #19)

- Hatchling's `version` build hook in `pattern = true` mode **rewrites the tracked file in place** in the working tree,
  on `uv build` and on editable `uv sync`, and never reverts it. With `cache-keys` that dirties every checkout on
  every commit. Its default pattern also rejects an annotated `__version__: str = ...`. Don't use pattern mode.
- Use template mode instead: `[tool.hatch.build.hooks.version] path = "budge/_version.py"` writes a module that the
  root `.gitignore` ignores (`src/back-end/budge/_version.py`). The hook runs for editable installs too, and it
  appends the path to `build_data["artifacts"]`, so the wheel and sdist ship the gitignored file without an explicit
  `artifacts` entry. Building a wheel from the sdist (no `.git`) still gets the real version, from `PKG-INFO`.
- `budge/__init__.py` does `from budge._version import __version__` and falls back to `'0.0.0'` on
  `ModuleNotFoundError` (a copy-only `budge/` in an image). A committed `budge/_version.pyi` types the import for mypy
  in a fresh clone. Pyright passes once `_version.py` exists, which is always the case after `uv sync`. In a fresh
  clone before any sync it gives one `reportMissingModuleSource` warning (exit 0). The user accepted that and wants
  no `# pyright: ignore` there, because #2 turns on `reportUnnecessaryTypeIgnoreComment`, which would flag it in
  every synced environment. `_version.py` is in coverage `omit`.
- Test the fallback with `monkeypatch.setitem(sys.modules, 'budge._version', None)` plus `importlib.reload(budge)`,
  then `undo()` and reload again.
