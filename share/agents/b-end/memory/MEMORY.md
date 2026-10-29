# b-end memory

Index of b-end agent memories, one line per entry.

<!-- shared-memory:begin (generated from share/agents/_memory/MEMORY.md; edit that file instead) -->

Shared with every agent; these notes live in `share/agents/_memory/`.

- [CI runs every hook](_memory/ci-runs-every-hook.md) — CI never SKIPs a pre-commit hook; hooks install their own tools; fixers exit non-zero
- [Comments sparingly](_memory/comments-sparingly.md) — readable code/CI over explanatory comments; comment only what code can't say
- [Commit hook prefix](_memory/git-commit-hook-gotchas.md) — prepare-commit-msg prepends `type(#n):` (amends too); omit it, set `GIT_SKIP_OWNER_NAME=1`
- [gh:commit skill forks](_memory/gh-commit-skill-forks.md) — skill commits in the background; wait, then verify signature/prefix
- [GitHub stacked PRs](_memory/github-stacked-prs.md) — dependencies API rejects PRs; `Closes` links only once a PR targets `main`
- [PR review posting](_memory/pr-review-mcp.md) — post as the bot via `gh api` (MCP writes as the owner); bot PRs take COMMENT only; full-SHA commitID
- [Restacking across worktrees](_memory/git-worktree-restack.md) — `--update-refs` can't move a branch checked out in another worktree; use `--onto`
- [YAML key order](_memory/yaml-key-order.md) — sort object keys alphabetically; workflows lead with `name`, `on`, `permissions`; lists keep order

<!-- shared-memory:end -->

- [Stack rebase checks](feedback_stack-rebase-checks.md) — run checks on git-archive exports per tip; zsh doesn't word-split `$cmd`
- [uv-dynamic-versioning quirks](uv-dynamic-versioning-quirks.md) — hatchling not uv_build; fallback only for no .git; cache-keys; gitignored `_version.py`; sdist `only-include`
- [coverage sysmon vs contexts](coverage-sysmon-contexts.md) — keep `core = "ctrace"`; 3.14+ sysmon breaks `--cov-context=test`
- [ruff nested config first-party](ruff-nested-config-first-party.md) — `tests/ruff.toml` moves project root; keep `known-first-party`
- [local Python matrix](local-python-matrix.md) — 3.11–3.15 locally; uv 3.13.7 SIGKILL (137) history, fixed 2026-10-25; worktree Bash limits; taplo
- [pyright gotchas](pyright-gotchas.md) — `@contextmanager` needs `Generator`; nodenv; silent hang = pyright not in `.venv`; private-import from repo root; `__all__`
- [Explicit over implicit](feedback_explicit-over-implicit.md) — protocol impls subclass with `@override`; complete `__all__` (`tests/test_exports.py`), loggers exempt
- [Strict and rigorous](feedback_strict-and-rigorous.md) — strict types/lint/format; fix data to fit strict types, never loosen them
- [Three type checkers](project_type-checkers.md) — mypy, pyright and ty all run strict (user, 2026-10-20); a change passes all three
- [Starlette TestClient and httpx2](starlette-testclient-httpx2.md) — TestClient needs `httpx2`; list routes with `iter_route_contexts`; overrides per app
- [Mangum event loop](mangum-event-loop.md) — rootdir conftest.py owns Mangum's import-time loop (doctests too); async tests unset it; run the full matrix
- [Pydantic model notes](pydantic-model-notes.md) — field and route docstrings become OpenAPI text (routes pass `description=`); leaf models.py; FiniteFloat; strict
- [ruff over pylint](feedback_ruff-over-pylint.md) — ruff owns any check it has a rule for (preview by code); pylint keeps the rest; naming in ruff; tests W0621 via plugin
- [Lambda logging format](lambda-logging-format.md) — text vs JSON format; run summary logs `extra` `summary`/`failed_connections`; test via `vars(record)`
- [FastAPI app settings](fastapi-app-settings.md) — redirect_slashes=False (Host-derived 307 leaves CloudFront origin); operationId = route.name
- [FastAPI docs CDN pinning](fastapi-docs-cdn-pinning.md) — exact jsdelivr releases ≥2 weeks old; favicon `data:,` not ''; helpers allow no SRI; redoc stays 2.x
- [Route gating tests](feedback_route-gating-tests.md) — pin (method, path) pairs; gate by a denial marker, not == 200; fail-open stub ships a tripwire
- [Back-end hooks via uv](back-end-hooks-uv.md) — `language: python` + pinned uv, `uv run -q --locked`; VIRTUAL_ENV warning
- [CloudFront viewer IP](cloudfront-viewer-ip.md) — request.client is the CloudFront edge; read cloudfront-viewer-address for the viewer IP
