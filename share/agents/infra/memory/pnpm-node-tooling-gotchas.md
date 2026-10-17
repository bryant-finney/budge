---
name: pnpm-node-tooling-gotchas
description: pnpm 12 lockfile vs check-yaml, nodenv vs major-only .node-version, global gitignore hiding .node-version
metadata:
  type: project
---

# pnpm and Node tooling gotchas

Found while building the root pnpm workspace (#12, 2026-10-17).

- **pnpm 12 writes `pnpm-lock.yaml` as two YAML documents** (the first pins pnpm itself under
  `packageManagerDependencies`). The `check-yaml` hook fails on it unless it runs with
  `--allow-multiple-documents`. yamllint skips the lockfile through `ignore:` in `.yamllint.yaml`,
  which still applies when pre-commit passes the file by name.
- **`.node-version` is `24` (major only) so CI's setup-node picks up the latest 24.x.** nodenv 1.6
  cannot resolve a major-only version (`nodenv: version '24' is not installed`). Locally, set
  `NODENV_VERSION=24.x.y`, or add a `~/.nodenv/versions/24` symlink or the nodenv-aliases plugin.
  pre-commit's node hooks were unaffected.
- **The maintainer's global gitignore (`~/.config/git/ignore`) ignores `.node-version`.** The repo
  `.gitignore` re-includes it with `!.node-version`, so check `git status` after adding dotfiles.
- **`prettier-plugin-svelte` peers `svelte`.** pnpm's `autoInstallPeers` puts it in the root
  lockfile, which is expected, and the version changes once `front-end` declares `svelte`.
- **Agent sessions:** the worktree guard rejects Bash commands that mention the scratchpad path,
  because the path contains `github`. Run pnpm through `npx --yes pnpm@<ver>` instead of a
  scratchpad install.

**Why:** these are the steps of #12 that took more than one try.
**How to apply:** check these first when changing root tooling, hooks or the Node pin. See also
[[ci-node-setup]].
