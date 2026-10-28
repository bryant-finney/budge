# infra memory

Index of infra agent memories, one line per entry.

- [Comments sparingly](comments-sparingly.md) — readable code/CI over explanatory comments; comment only what code can't say
- [Config validation gotchas](config-validation-gotchas.md) — ICU vs IANA zone names, Intl over-acceptance, Scheduler rate units
- [Commit hook prefix](git-commit-hook-gotchas.md) — prepare-commit-msg prepends `feat(#n):` (amends too); omit it, set `GIT_SKIP_OWNER_NAME=1`
- [pnpm/Node tooling gotchas](pnpm-node-tooling-gotchas.md) — pnpm 12 lockfile vs check-yaml, nodenv vs `.node-version`, skeleton packages, coverage proofs
- [Pulumi mock test harness](pulumi-mock-test-harness.md) — drain `setMocks` RPCs with `runtime.disconnect()` before asserting resources
- [Restacking across worktrees](git-worktree-restack.md) — `--update-refs` can't move a branch checked out in another worktree; use `--onto`
- [Required checks: one aggregator](required-checks-aggregator.md) — require only `ci-ok` (always(), skipped=fail), never per-matrix contexts
- [YAML key order](yaml-key-order.md) — sort object keys alphabetically; workflows lead with `name`, `on`, `permissions`; lists keep order
