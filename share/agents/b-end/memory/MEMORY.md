# b-end memory

Index of b-end agent memories, one line per entry.

- [Stack rebase checks](feedback_stack-rebase-checks.md) — run checks on git-archive exports per tip; zsh doesn't word-split `$cmd`
- [PR review via gh MCP](feedback_pr-review-mcp.md) — omit/full-SHA commitID on create; owner PRs take COMMENT only
- [uv-dynamic-versioning quirks](uv-dynamic-versioning-quirks.md) — hatchling not uv_build; fallback-version only for no .git; cache-keys; full CI fetch; gitignored `_version.py`, not hook pattern mode
- [Commit hook prefix](commit-msg-hook-prefix.md) — prepare-commit-msg prepends `type(#N):` from the branch; write bare subjects
- [coverage sysmon vs contexts](coverage-sysmon-contexts.md) — keep `core = "ctrace"`; 3.14+ sysmon breaks `--cov-context=test`
- [ruff nested config first-party](ruff-nested-config-first-party.md) — `tests/ruff.toml` moves project root; keep `known-first-party`
- [local Python matrix](local-python-matrix.md) — 3.11–3.15 locally; uv 3.13.7 SIGKILL (137) history, fixed 2026-10-25; worktree Bash limits; taplo
- [gh:commit skill forks](gh-commit-skill-forks.md) — skill commits in the background; wait, then verify signature/prefix
- [GitHub stacked PRs](github-stacked-prs.md) — dependencies API rejects PRs; `Closes` links only once a PR targets `main`
- [pyright gotchas](pyright-gotchas.md) — `@contextmanager` needs `Generator`; nodenv; silent hang = pyright not in `.venv`; private-import from repo root; `__all__`
- [Explicit over implicit](feedback_explicit-over-implicit.md) — protocol impls subclass with `@override`; complete `__all__` (`tests/test_exports.py`), loggers exempt
- [Strict and rigorous](feedback_strict-and-rigorous.md) — strict types/lint/format; fix data to fit strict types, never loosen them
- [Three type checkers](project_type-checkers.md) — mypy, pyright and ty all run strict (user, 2026-10-20); a change passes all three
- [Starlette TestClient and httpx2](starlette-testclient-httpx2.md) — TestClient needs `httpx2`; list routes with `iter_route_contexts`; overrides per app
- [Mangum event loop](mangum-event-loop.md) — conftest owns Mangum's import-time loop; async tests unset it; run the full matrix
- [Pydantic model notes](pydantic-model-notes.md) — field and route docstrings become OpenAPI text (routes pass `description=`); leaf models.py; FiniteFloat; strict
- [ruff over pylint](feedback_ruff-over-pylint.md) — ruff owns any check it has a rule for (preview by code); pylint keeps the rest; naming in ruff; tests W0621 via plugin
- [Lambda logging format](lambda-logging-format.md) — text vs JSON format; run summary logs `extra` `summary`/`failed_connections`; test via `vars(record)`
- [FastAPI app settings](fastapi-app-settings.md) — redirect_slashes=False (Host-derived 307 leaves CloudFront origin); operationId = route.name
- [FastAPI docs CDN pinning](fastapi-docs-cdn-pinning.md) — exact jsdelivr releases ≥2 weeks old; favicon `data:,` not ''; helpers allow no SRI; redoc stays 2.x
