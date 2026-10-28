# infra memory

Index of infra agent memories, one line per entry.

<!-- shared-memory:begin (generated from share/agents/_memory/MEMORY.md; edit that file instead) -->

Shared with every agent; these notes live in `share/agents/_memory/`.

- [CI runs every hook](../../_memory/ci-runs-every-hook.md) — CI never SKIPs a pre-commit hook; hooks install their own tools; fixers exit non-zero
- [Comments sparingly](../../_memory/comments-sparingly.md) — readable code/CI over explanatory comments; comment only what code can't say
- [Commit hook prefix](../../_memory/git-commit-hook-gotchas.md) — prepare-commit-msg prepends `type(#n):` (amends too); omit it, set `GIT_SKIP_OWNER_NAME=1`
- [gh:commit skill forks](../../_memory/gh-commit-skill-forks.md) — skill commits in the background; wait, then verify signature/prefix
- [GitHub stacked PRs](../../_memory/github-stacked-prs.md) — dependencies API rejects PRs; `Closes` links only once a PR targets `main`
- [PR review posting](../../_memory/pr-review-mcp.md) — omit/full-SHA commitID; owner PRs take COMMENT only; `gh api` reviews from a JSON file
- [Restacking across worktrees](../../_memory/git-worktree-restack.md) — `--update-refs` can't move a branch checked out in another worktree; use `--onto`
- [YAML key order](../../_memory/yaml-key-order.md) — sort object keys alphabetically; workflows lead with `name`, `on`, `permissions`; lists keep order

<!-- shared-memory:end -->

- [Config validation gotchas](config-validation-gotchas.md) — ICU vs IANA zone names, Intl over-acceptance, Scheduler rate units
- [pnpm/Node tooling gotchas](pnpm-node-tooling-gotchas.md) — pnpm 12 lockfile vs check-yaml, nodenv vs `.node-version`, skeleton packages, coverage proofs
- [Pulumi mock test harness](pulumi-mock-test-harness.md) — drain `setMocks` RPCs with `runtime.disconnect()` before asserting resources
- [Required checks: one aggregator](required-checks-aggregator.md) — require only `ci-ok` (always(), skipped=fail), never per-matrix contexts
