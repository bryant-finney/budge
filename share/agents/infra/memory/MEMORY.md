# infra memory

Index of infra agent memories, one line per entry.

- [Config validation gotchas](config-validation-gotchas.md) — ICU vs IANA zone names, Intl over-acceptance, Scheduler rate units
- [Commit hook prefix](git-commit-hook-gotchas.md) — prepare-commit-msg prepends `feat(#n):`; omit it from messages
- [pnpm/Node tooling gotchas](pnpm-node-tooling-gotchas.md) — pnpm 12 lockfile vs check-yaml, nodenv vs `.node-version`, skeleton packages, coverage proofs
- [Pulumi mock test harness](pulumi-mock-test-harness.md) — drain `setMocks` RPCs with `runtime.disconnect()` before asserting resources
- [Restacking across worktrees](git-worktree-restack.md) — `--update-refs` can't move a branch checked out in another worktree; use `--onto`
