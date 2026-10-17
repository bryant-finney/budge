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
- **`.node-version` pins a full patch version (e.g. `24.22.0`), not `24`.** nodenv 1.6 cannot
  resolve a major-only version (`nodenv: version '24' is not installed`). On 2026-10-17 the user
  chose a full pin over local aliases. After a bump, run `nodenv install <version>` locally;
  until then `NODENV_VERSION=<installed 24.x>` only works for frozen installs: with `engineStrict`,
  `pnpm add`/`pnpm update` also enforce each dependency's `engines.node` (jsdom@30 needs `^24.15.0`).
  Dependabot doesn't bump `.node-version`; the bump mechanism is tracked in #15.
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
