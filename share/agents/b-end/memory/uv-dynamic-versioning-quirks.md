---
name: uv-dynamic-versioning-quirks
description: uv-dynamic-versioning needs hatchling (not uv_build); fallback-version is for missing .git, not missing tags; needs cache-keys and full CI checkout
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
