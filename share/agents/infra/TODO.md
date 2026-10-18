# infra TODO

Progress handoff for a cold-started infra agent. Last updated on 2026-10-18, after the #21/#22
review fixes, with `main` at `11bcb76` (#19 merged). Verify each SHA and count with
`git fetch origin` before acting.

## Stack state

| PR  | Branch                      | Base                      | Head              | Ahead of `main` | Behind `main` |
| --- | --------------------------- | ------------------------- | ----------------- | --------------- | ------------- |
| #21 | `feat/13/pulumi-skeleton`   | `main`                    | `d3a4c91`         | 6               | 0             |
| #22 | `chore/14/pre-commit-hooks` | `feat/13/pulumi-skeleton` | this branch's tip | 13              | 0             |

- **The restack is done.** Both PRs are 0 behind `main` (`11bcb76`).
- **How to restack (next time `main` moves):** from the `chore/14` tip, run
  `git rebase --update-refs origin/main`. That moves `feat/13` too. Don't rebase each branch on its own, which duplicates the parent's commits.
  Check `git range-diff` (every patch `=`), then push bottom-up with
  `git push --force-with-lease=<branch>:<old sha> origin <branch>`. Afterwards the ahead counts
  must be unchanged, and both behind counts 0.
- **Checks to rerun on each tip:** `pnpm --filter infrastructure exec tsc --noEmit`,
  `... exec eslint .`, `... exec vitest run`, `pnpm run format:check` (from the root) and
  `pre-commit run --all-files`. If `pnpm` isn't on `PATH`, use the `.cache/bin/pnpm` shim (see
  [pnpm-node-tooling-gotchas](memory/pnpm-node-tooling-gotchas.md)).

## #21 `feat/13/pulumi-skeleton`

Review: <https://github.com/bryant-finney/budge/pull/21#pullrequestreview-5560891942>

- [x] **Medium (fixed in `d3a4c91`):** `src/infrastructure/tests/program.test.ts:75`. The "creates no resources" test
  can't fail, because registration is async and `registered` is still empty when it's checked.
  Fix: change `beforeAll(setMocks…)` (L33) to `beforeEach`, and in `runProgram` run
  `await pulumi.runtime.disconnect()` after `await import('../index.js')`. Prove it by injecting a
  `CustomResource` into `index.ts` once and watching the test fail. See
  [pulumi-mock-test-harness](memory/pulumi-mock-test-harness.md).
- [x] **Nit, PR body (edited):** it says the checks ran on Node 24.9.0 via `NODENV_VERSION`, with
  `engines.node` `>=24 <25`. The tip uses `>=24.15 <25` with `engineStrict` and the
  `.node-version` pin `24.22.0`. The "Blocked by #18 / targets `chore/12/pnpm-workspace`" lines
  are stale too, because the base is now `main`. Edit the body; no commit is needed.
- [ ] **Still pending:** the `pulumi stack init smoke … && pulumi preview` smoke test from #13.
  The Pulumi CLI isn't installed on this machine (as of 2026-10-18). Only an emulation of the
  runtime's ts-node 7 loading path has been verified.
- [ ] **Open review, 2026-10-18** (<https://github.com/bryant-finney/budge/pull/21#pullrequestreview-5563602971>):
  the user decides on these. Medium: `config.ts:41`. `Intl.supportedValuesOf('timeZone')` rejects
  `Asia/Kolkata`, `Europe/Kyiv` and `UTC`. Low: `config.ts:49`. `schedule_rate` isn't
  validated. Low: `bootstrap.sh:17-22`. The plan doesn't name the state bucket's SSE type, and it
  leaves out a TLS-only policy, KMS rotation and noncurrent-version expiry.
- **Notes for milestone 4 (not blocking #21):** when the `bootstrap.sh` deploy role is
  implemented, scope its GitHub OIDC trust to `main` or a deploy environment, not every workflow
  or PR. Also give it permissions for the stack's resources, not only for the state bucket and the
  KMS key.

## #22 `chore/14/pre-commit-hooks`

Review: <https://github.com/bryant-finney/budge/pull/22#pullrequestreview-5560882430>

- [x] **Issue (fixed):** `.pre-commit-config.yaml:63-64`. The shellcheck `files: (^\.envrc$|\.sh$)`
  override is ANDed with the manifest's `types: [shell]`, so it narrows coverage: executable
  scripts without an extension are skipped. Its comment ("however identify tags it") is also
  wrong. Drop both lines; the defaults still check `.envrc` and `bootstrap.sh`.
- [x] **Nit (fixed):** `.pre-commit-config.yaml:86` (eslint) and `:92` (tsc). Widen `files:` so both
  hooks rerun when their inputs change, for example by adding
  `|src/infrastructure/(package|tsconfig.*)\.json|pnpm-lock\.yaml|tsconfig\.base\.json`.
- [x] **Nit, for #15 (hook comment added; the runner pin is still #15's):** `.pre-commit-config.yaml:69`. actionlint shellchecks
  `run:` blocks only when a `shellcheck` binary is on `PATH`; the `shellcheck-py` hook env doesn't
  count. Pin shellcheck on the runner, or say so in the hook comment.

## #25 `docs/17/rules-bypass-always` (merged)

Review: <https://github.com/bryant-finney/budge/pull/25#pullrequestreview-5560873964>

All four findings are fixed on `main` (`8ba6f0e`), so none needs a follow-up:

- The no-push-to-`main` rule is now in the "Merging and pushing" section of all three `AGENT.md`s
  (`b-end`, `f-end` and `infra`), and ruleset `main-history` blocks force-pushing and deleting
  `main` for everyone. What's left is stated in `rules.md`: a session that loads none of those
  agents has no guard against a plain push to `main`. A shared root instruction file would close
  that gap if the owner wants it.
- `rules.md` now says how to set the mode back: change the Bypass row to `pull_request` in a PR,
  then `apply`.
- The Context section no longer contradicts the bypass note.
- The `update`-without-parameters note now gives the reason and the cost.

## Housekeeping

- [ ] Remove the `.claude/worktrees/agent-infra-rules-bypass-always` worktree (at `f8ee673`) and
  its local branch `docs/17/rules-bypass-always`. #25 has merged, and GitHub already deleted the
  remote branch. Not done yet; ask before removing another agent's worktree.

## Gotchas

- **Commit subjects:** the repo's `prepare-commit-msg` hook prepends `<type>(#N):` from the
  branch name, for example `chore(#14):` on `chore/14/...` (`GIT_SKIP_OWNER_NAME=1` gives `#14`
  rather than `owner/repo#14`). It doesn't notice an existing prefix, so pass only the subject:
  `GIT_SKIP_OWNER_NAME=1 git commit --signoff --gpg-sign -m "<subject>"`. Don't commit with an
  empty message; the hook fills one in from whatthecommit.com.
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
