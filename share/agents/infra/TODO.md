# infra TODO

Progress handoff for a cold-started infra agent. Last updated on 2026-10-20, after the stack was
rebased onto `main` at `e7b4c8e` (#23 merged). Verify each SHA and count with `git fetch origin`
before acting.

## Stack state

| PR  | Branch                      | Base                      | Worktree                  | Head              | Ahead of `main` | Behind `main` |
| --- | --------------------------- | ------------------------- | ------------------------- | ----------------- | --------------- | ------------- |
| #21 | `feat/13/pulumi-skeleton`   | `main`                    | `.claude/worktrees/pr-21` | `e2d854e`         | 12              | 0             |
| #22 | `chore/14/pre-commit-hooks` | `feat/13/pulumi-skeleton` | `.claude/worktrees/pr-22` | this branch's tip | 22 (10 own)     | 0             |

- **Checks on both tips (2026-10-20), all green:** `tsc --noEmit`, `eslint .`, `vitest run`
  (26 tests), `pnpm run format:check`, `pre-commit run --all-files`, and `shellcheck src/infrastructure/*.sh`. `actionlint` exits 3 ("no project was found") only because there is
  no `.github/workflows/` yet; that arrives with #15.
- **How to restack (next time `main` moves).** Each branch is checked out in its own worktree, so
  `git rebase --update-refs` can't move `feat/13` from the #22 worktree. Instead:
  1. In `pr-21`: `git rebase origin/main` (note the old tip first).
  2. In `pr-22`: `git rebase --onto feat/13/pulumi-skeleton <old #21 tip> chore/14/pre-commit-hooks`.
  3. Check `git range-diff` (every patch `=`), then push bottom-up with
     `git push --force-with-lease=<branch>:<old sha> origin <branch>`.
  4. The ahead counts must be unchanged, and both behind counts 0.
- **Rebased SHAs.** Issue #13's checklist and the PR threads cite pre-rebase SHAs. The patches are
  identical (`git patch-id`): `d3a4c91` = `a831c7d`, `f409bb4` = `2d43e47`, `069c53c` = `6f44205`,
  `337e1df` = `f727f8a`, `1732e1a` = `f1b55de`, `eea976a` = `5a46610`, `89b39c4` = `81512e6`.
- If `pnpm` isn't on `PATH`, use the `.cache/bin/pnpm` shim (see
  [pnpm-node-tooling-gotchas](memory/pnpm-node-tooling-gotchas.md)).

## #21 `feat/13/pulumi-skeleton`

No code work is open. Every #13 acceptance box is checked.

- [x] **Review round 1** (<https://github.com/bryant-finney/budge/pull/21#pullrequestreview-5560891942>):
  the mock-runtime drain (`a831c7d`) and the PR-body nit are done.
- [x] **Review round 3** (<https://github.com/bryant-finney/budge/pull/21#pullrequestreview-5563602971>):
  all three threads are answered (`6f44205`, `f727f8a`). They stay unresolved until the user
  resolves them; don't resolve them yourself.
- [x] **Smoke test:** `pulumi preview` on a throwaway local file backend passed at `d3a4c91`, and
  again at `e2d854e` (2026-10-20) with `household_timezone=Asia/Kolkata`. `schedule_rate=rate(4 hour)`
  fails with `ConfigPatternError`, as intended. Recipe:
  [pulumi-mock-test-harness](memory/pulumi-mock-test-harness.md).
- [ ] **Awaiting the user:** merge. Two commit subjects carry a doubled `feat(#13): feat(#13):`
  prefix (`6f44205`, `f727f8a`). Rewording them takes a force-push and a #22 restack, so it's the
  user's call.
- **Notes for milestone 4 (not blocking #21):** when the `bootstrap.sh` deploy role is
  implemented, give it permissions for the stack's resources, not only for the state bucket and
  the KMS key. Settle whether Scheduler accepts `rate(1 hour)` on the first real `pulumi up`.

## #22 `chore/14/pre-commit-hooks`

- [x] **Review round 1** (<https://github.com/bryant-finney/budge/pull/22#pullrequestreview-5560882430>):
  the shellcheck selection fix, the widened eslint/tsc triggers and the actionlint comment are in
  `5a46610`. Pinning shellcheck on the runner is #15's.
- [ ] **Awaiting the user** (review of 2026-10-18T15:14Z):
  - **Low** `.pre-commit-config.yaml:78`: drop `--ignore-unknown` from the prettier entry? #14's
    table prescribes the flag; the reviewer showed it hides a missing parser. Recommended: drop it.
  - **Medium-low** this file: keep it as a living handoff (b), drop it from the PR (a), or fold
    its lasting notes into `memory/` and delete it before #22 merges (c). Until the user picks, each
    infra session keeps it current.

## Housekeeping

- [x] The `agent-infra-rules-bypass-always` worktree and its local branch
  `docs/17/rules-bypass-always` are gone (checked 2026-10-20).

## Gotchas

- **Commit subjects:** the repo's `prepare-commit-msg` hook prepends `<type>(#N):` from the
  branch name, for example `chore(#14):` on `chore/14/...` (`GIT_SKIP_OWNER_NAME=1` gives `#14`
  rather than `owner/repo#14`). It doesn't notice an existing prefix, so pass only the subject:
  `GIT_SKIP_OWNER_NAME=1 git commit --signoff --gpg-sign -m "<subject>"`. Don't commit with an
  empty message; the hook fills one in from whatthecommit.com.
- **`git commit --amend` runs the hook again.** `--amend --no-edit` without
  `GIT_SKIP_OWNER_NAME=1` gave `chore(worktrees/pr-22#14): chore(#14): ...` (2026-10-18). Amend with
  `GIT_SKIP_OWNER_NAME=1 git commit --amend --signoff --gpg-sign -F <file>`, where the file holds
  the bare subject plus trailers, then check `git log -1 --format=%B` before pushing. Leaving out
  `--signoff` on an amend drops the `Signed-off-by` trailer.
- **`fatal: ref HEAD is not a symbolic ref` during a rebase is harmless.** The hook runs on the
  detached HEAD, can't read the branch, and adds no prefix, so each picked commit keeps its
  original message. Confirm with `git range-diff`.

## Next infra issues

- #15: PR CI workflow (pre-commit, TS checks, Python matrix, `ci-ok` gate) plus Dependabot for
  actions. It picks up the #22 actionlint nit and the `.node-version` bump mechanism.
- #16: a disabled `main` deploy workflow stub (OIDC permissions, gated on `DEPLOY_ENABLED`).
- #17: repo settings as code. The rulesets and merge settings have landed (#24, #25). There's
  still no `CODEOWNERS` file on `main` (checked 2026-10-18), although the
  `require_code_owner_review` note in `rules.md` assumes one gives every path to `@bryant-finney`.
  Check what else the issue lists (security and Actions settings) before closing it.
