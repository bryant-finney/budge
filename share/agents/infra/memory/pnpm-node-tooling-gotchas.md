---
name: pnpm-node-tooling-gotchas
description: pnpm 12 lockfile vs check-yaml, nodenv vs major-only .node-version, global gitignore hiding .node-version, skeleton packages, proving tool coverage
metadata:
  type: project
---

# pnpm and Node tooling gotchas

Found while building the root pnpm workspace (#12, 2026-10-17).

- **pnpm 12 writes `pnpm-lock.yaml` as two YAML documents** (the first pins pnpm itself under
  `packageManagerDependencies`). `check-yaml` is split in two: the main entry excludes the lockfile,
  and a second entry runs `--allow-multiple-documents` on the lockfile only. Applying the flag
  globally would let a stray `---` through in workflow files. yamllint skips the lockfile through
  `ignore:` in `.yamllint.yaml`,
  which still applies when pre-commit passes the file by name.
- **`.node-version` pins a full patch version (e.g. `24.22.0`), not `24`.** nodenv 1.6 cannot
  resolve a major-only version (`nodenv: version '24' is not installed`). On 2026-10-17 the user
  chose a full pin over local aliases. **Don't set `NODENV_VERSION`** (user, PR #18 review): nodenv
  on the maintainer's machine provides the version `.node-version` names, so run everything under
  that exact pin.
  Dependabot doesn't bump `.node-version`; the bump mechanism is tracked in #15.
- **`engineStrict` checks every dependency's `engines.node`, not just the root's.** On `pnpm add`
  and `pnpm update` (not on frozen installs), it fails with `ERR_PNPM_UNSUPPORTED_ENGINE` when a
  dependency has a higher floor. jsdom@30 needs `^24.15.0`, so the root range is `>=24.15 <25`.
  Raise the root floor when a dependency raises its own. An up-to-date `node_modules`
  short-circuits a plain `pnpm install`, so the gate only holds for fresh and `--frozen-lockfile`
  installs.
- **pnpm 12 copies `packageManager` into `pnpm-lock.yaml` (`packageManagerDependencies`).** A bump
  to `package.json#packageManager` alone fails `pnpm install --frozen-lockfile`
  (`ERR_PNPM_FROZEN_LOCKFILE_WITH_OUTDATED_LOCKFILE`), so the bump must also run `pnpm install`
  and commit the lockfile (#15).
- **The maintainer's global gitignore (`~/.config/git/ignore`) ignores `.node-version`.** The repo
  `.gitignore` re-includes only the root file with `!/.node-version` (anchored, so per-package
  `nodenv local` pins stay ignored). Check `git status` after adding dotfiles.
- **`tsconfig.base.json` is extended last by front-end**
  (`"extends": ["$app/tsconfig", "../../tsconfig.base.json"]`; SvelteKit 3 has no
  `.svelte-kit/tsconfig.json`), so its options override SvelteKit's. Never add `types`, `paths`,
  `include`, `rootDirs`, `isolatedModules` or `verbatimModuleSyntax` there, or the front-end
  breaks. The base holds only options every package shares (user decision, PR #21, 2026-10-18). The tsconfigs must stay comment-free, so this constraint lives here, in #12 and
  in PR #18.
- **Prettier and `.claude/worktrees/`:** agent worktrees are full repo copies whose `.git` is a
  file, so Prettier doesn't skip them. `.prettierignore` lists `.claude/worktrees/`.
- **`prettier-plugin-svelte` peers `svelte`.** pnpm's `autoInstallPeers` puts it in the root
  lockfile, which is expected, and the version changes once `front-end` declares `svelte`.
- **Skeleton packages (PR #18 review):** both packages exist from #12 on, with only a `check`
  script (`tsc --noEmit`). The infrastructure tsconfig already carries #13's CommonJS options, so
  #13 only widens `include`. The front-end tsconfig sets `target`/`lib`/`module`/
  `moduleResolution` itself; #6 drops them when it switches to `$app/tsconfig`, which sets them.
- **TS packages are flat, with no nested `src/`** (user decision, 2026-10-17), like
  `src/back-end/budge/`: `src/front-end/lib/index.ts`, `src/infrastructure/config.ts`. SvelteKit
  takes `sveltekit({ files: { src: '.' } })` (#6 must verify that dev/build/svelte-check/Vitest
  don't scan `node_modules`, `build/` or `.svelte-kit/`; the fallback is a non-`src` dir such as
  `src/front-end/app/`). Kit 3 dropped `$lib`, so `src/front-end/package.json` declares
  `"imports": { "#lib": "./lib/index.ts", "#lib/*": "./lib/*" }`. The docs show a `.js` target
  (`./src/lib/index.js`). Both resolve in tsc (bundler) and Vite 8, but only the `.ts` target
  resolves in plain Node 24 (`ERR_MODULE_NOT_FOUND`), so the target names the real file.
- **Proving coverage:** `prettier --check` lists only failing files. To count what it reaches,
  run `prettier --write .` on a clean tree: Prettier 3 logs every matched file as `(unchanged)`.
  For tsc, use `tsc --noEmit --listFilesOnly | grep -v node_modules`.
- **`pnpm -r run` stops at the first failing package and kills the others** (SIGKILL), so root
  `pnpm run check` reports only one package's errors. To see every failure (e.g. when proving
  negative probes), run `pnpm -C <pkg> run check` per package, or pass `--no-bail`.
- **`verbatimModuleSyntax` conflicts with CommonJS output, so it lives in
  `src/front-end/tsconfig.json`, not the base.** `src/infrastructure` is CommonJS
  (`module: nodenext`, no `"type": "module"`) for Pulumi's runtime, where the option makes TS reject
  ESM syntax (TS1295/TS1287). Infrastructure overrides nothing from the base: it adds
  `isolatedModules: true`, because Vitest transpiles each file on its own, and it relies on eslint
  `consistent-type-imports` for explicit type imports. The user moved the option out of the base on
  PR #21, 2026-10-18. Dynamic `import()` still
  needs the `.js` extension in a CJS file under nodenext. Name the Vitest config `.mts`, or Vite
  warns about ESM syntax in a CJS-loaded file.
- **pnpm 12's release-age gate edits `pnpm-workspace.yaml` during install.** A dependency version
  younger than `minimumReleaseAge` makes `pnpm install` append it to `minimumReleaseAgeExclude`
  without asking. Revert that and pin a version that clears the gate (#13 used `@pulumi/pulumi`
  3.269.0, not 3.270.0, which was less than a day old). New build scripts (e.g. `protobufjs`) need
  an explicit `allowBuilds` entry, or install fails with `ERR_PNPM_IGNORED_BUILDS`.
- **pre-commit file selection (#14):** identify tags `.mjs` as `javascript` but gives `.mts`/`.cts`
  no `ts` tag, so the shared `prettier` hook selects by extension (`files:`) instead of `types_or`.
  `.envrc` has a bash shebang (for shellcheck's dialect) but must not be executable, so it is
  excluded from `check-shebang-scripts-are-executable`. The `repo: local` hooks are
  `language: system` and need `pnpm` on `PATH`. On a machine without global pnpm, use the
  `.cache/bin/pnpm` shim from the next bullet (`.cache` is in `.gitignore`). These hooks type-check
  only `src/infrastructure`; front-end's `check` gets a hook in #10 (`front-end-svelte-check`).
- **Agent sessions:** the worktree guard rejects Bash commands that mention the scratchpad path,
  because the path contains `github`. Run pnpm through `npx --yes pnpm@<ver>` instead of a
  scratchpad install. zsh doesn't word-split `P="npx --yes pnpm@<ver>"; $P ...`, so put a
  git-ignored `.cache/bin/pnpm` shim (`exec npx --yes pnpm@<ver> "$@"`) on `PATH` instead.

**Why:** these are the steps of #12 that took more than one try.
**How to apply:** check these first when changing root tooling, hooks or the Node pin. See also
[[ci-node-setup]].
