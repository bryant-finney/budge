# b-end memory

Index of b-end agent memories, one line per entry.

- [Stack rebase checks](feedback_stack-rebase-checks.md) — run checks on git-archive exports per tip; zsh doesn't word-split `$cmd`
- [PR review via gh MCP](feedback_pr-review-mcp.md) — omit/full-SHA commitID on create; owner PRs take COMMENT only
- [uv-dynamic-versioning quirks](uv-dynamic-versioning-quirks.md) — hatchling not uv_build; fallback-version only for no .git; cache-keys; full CI fetch; gitignored `_version.py`, not hook pattern mode
- [Commit hook prefix](commit-msg-hook-prefix.md) — prepare-commit-msg prepends `type(#N):` from the branch; write bare subjects
