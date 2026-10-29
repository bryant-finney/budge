# Shared memory

Index of memories that apply to every agent, one line per entry. `bin/sync-shared-memory` copies these
lines into each agent's `MEMORY.md`.

- [CI runs every hook](ci-runs-every-hook.md) — CI never SKIPs a pre-commit hook; hooks install their own tools; fixers exit non-zero
- [Comments sparingly](comments-sparingly.md) — readable code/CI over explanatory comments; comment only what code can't say
- [Commit hook prefix](git-commit-hook-gotchas.md) — prepare-commit-msg prepends `type(#n):` (amends too); omit it, set `GIT_SKIP_OWNER_NAME=1`
- [gh:commit skill forks](gh-commit-skill-forks.md) — skill commits in the background; wait, then verify signature/prefix
- [GitHub stacked PRs](github-stacked-prs.md) — dependencies API rejects PRs; `Closes` links only once a PR targets `main`
- [PR review posting](pr-review-mcp.md) — post as the bot via `gh api` (MCP writes as the owner); bot PRs take COMMENT only; full-SHA commitID
- [Restacking across worktrees](git-worktree-restack.md) — `--update-refs` can't move a branch checked out in another worktree; use `--onto`
- [YAML key order](yaml-key-order.md) — sort object keys alphabetically; workflows lead with `name`, `on`, `permissions`; lists keep order
