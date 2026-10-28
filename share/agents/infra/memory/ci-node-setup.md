---
name: ci-node-setup
description: ci.yml setup order (pnpm before setup-node), uvx needs setup-uv, SKIP folding, colon-space in plain run scalars, admin-only GitHub settings unreadable by the bot and GITHUB_TOKEN
metadata:
  type: project
---

# CI workflow gotchas (#15–#17, 2026-10-27)

- **Setup order:** `pnpm/action-setup` (reads `packageManager`; supports pnpm 12) must run before
  `actions/setup-node` with `cache: pnpm`, which needs pnpm on PATH. The `pre-commit` job also
  needs `astral-sh/setup-uv` just to get `uvx`, with no `uv sync`.

- **`SKIP` over 120 chars:** a folded scalar (`>-`) puts a space after each comma. That is fine,
  because pre-commit's `_get_skips` strips each id.

- **`run: echo "TODO(M5): …"` as a plain scalar is invalid YAML** (`mapping values are not allowed`). Use `run: |` for any step text that contains a colon followed by a space. zizmor
  didn't catch it; actionlint and yamllint did.

- **Stacked PRs report `ci-ok`.** The workflow has no `branches:` filter, and the PRs based on
  other PR branches (#35, #38) ran the full CI. The first green run was
  [run 40551759086](https://github.com/bryant-finney/budge/actions/runs/40551759086) (PR #32).

- **`bryant-finney-bot` isn't a repo admin.** As the bot:

  - `actions/permissions*` returns 403.
  - `vulnerability-alerts` and `automated-security-fixes` return 404, the same as disabled.
  - `security_and_analysis` is `null`.
  - `apply-repo-rules.sh check` sees `bypass_actors: []`, so it reports false drift on `main`
    and `release-tags`.

  `GITHUB_TOKEN` has no `administration` scope either, so `repo-settings.sh` checks
  `permissions.admin` and refuses (exit 5). The check is local-only and the owner runs it.

- **The `.node-version` / `packageManager` bump mechanism is still undecided** (the first comment
  on #15; Renovate is recommended). It's the owner's call.

**Why:** each of these cost a retry or would have produced a false result.
**How to apply:** check these when editing workflows or the repo-settings check. See also
[[pnpm-node-tooling-gotchas]] and [[agent-worktree-isolation]].
