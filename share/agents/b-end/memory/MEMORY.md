# b-end memory

Index of b-end agent memories, one line per entry.

- [Stack rebase checks](feedback_stack-rebase-checks.md) — run checks on git-archive exports per tip; zsh doesn't word-split `$cmd`
- [PR review via gh MCP](feedback_pr-review-mcp.md) — omit/full-SHA commitID on create; owner PRs take COMMENT only
- [uv-dynamic-versioning quirks](uv-dynamic-versioning-quirks.md) — hatchling not uv_build; fallback-version only for no .git; cache-keys; full CI fetch; gitignored `_version.py`, not hook pattern mode
- [Commit hook prefix](commit-msg-hook-prefix.md) — prepare-commit-msg prepends `type(#N):` from the branch; write bare subjects
- [coverage sysmon vs contexts](coverage-sysmon-contexts.md) — keep `core = "ctrace"`; 3.14+ sysmon breaks `--cov-context=test`
- [ruff nested config first-party](ruff-nested-config-first-party.md) — `tests/ruff.toml` moves project root; keep `known-first-party`
- [local Python matrix](local-python-matrix.md) — running 3.11–3.15 locally, worktree Bash limits, taplo vs `uv.lock`
- [gh:commit skill forks](gh-commit-skill-forks.md) — skill commits in the background; wait, then verify signature/prefix
- [GitHub stacked PRs](github-stacked-prs.md) — dependencies API rejects PRs; `Closes` links only once a PR targets `main`
- [pyright gotchas](pyright-gotchas.md) — `@contextmanager` needs `Generator`; nodenv; silent hang = pyright not in `.venv`; private-import from repo root; `__all__`
- [Explicit over implicit](feedback_explicit-over-implicit.md) — protocol impls subclass with `@override`; complete `__all__` everywhere (`tests/test_exports.py`)
- [Three type checkers](project_type-checkers.md) — mypy, pyright and ty all run strict (user, 2026-10-20); a change passes all three
