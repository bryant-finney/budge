# f-end memory

Index of f-end agent memories, one line per entry.

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
