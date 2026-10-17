# Repository protection spec

This is the desired state for branch, tag, and merge protection on
[`bryant-finney/budge`](https://github.com/bryant-finney/budge). **infra** owns it: infra applies
it, keeps the live GitHub settings in line with it, and updates this file first whenever a rule
changes. It is written for both the user and coding agents. People should read the rationale
sections, and agents should follow [Desired state](#desired-state) and
[Procedures](#procedures).

## Context

- The repo is public and owned by a user account on GitHub Free. Rulesets are available. The
  `evaluate` (dry-run) enforcement mode is Enterprise-only, so every ruleset here is `active`.
- There is one human, `bryant-finney` (repo admin). Coding agents (b-end, f-end, infra) run as
  that same account and sign their commits with the same GPG key.
- Agents open stacked PRs: one per issue, with branches named `<type>/<issue#>/<slug>`. Each PR
  usually targets the previous issue's branch rather than `main`. When a parent PR merges, GitHub
  retargets the child to `main`. `delete_branch_on_merge` is on.
- PRs are merged with merge commits (the first was PR #18, merged as `a3a760f`). Local commits are
  GPG-signed. Commits made through the web UI (merge button, applied review suggestions) are
  signed by GitHub's web-flow key. That key isn't in the local keyring, so
  `git log --format=%G?` shows `E` for those commits, but GitHub reports them `verified: true`.
- Required status checks wait until CI workflows exist. See [Future CI](#future-ci).

## Desired state

The tables in [`rules.md`](../../skills/apply-repo-rules/rules.md) are the desired state, and the
[`apply-repo-rules`](../../skills/apply-repo-rules/SKILL.md) script reads them. They define three
items:

- **Ruleset `main`** (branch: `~DEFAULT_BRANCH` and `refs/heads/main`): `deletion`,
  `non_fast_forward`, `required_signatures`, and `pull_request` with merge commits only, 0
  approvals, and thread resolution required.
- **Ruleset `release-tags`** (tag: `refs/tags/v*`): `deletion`, `non_fast_forward`, and `update`.
- **Repository merge settings**: merge commits on, squash and rebase off, "Update branch" on.

Nothing else is protected. In particular, feature branches and tags that don't start with `v`
have no rules.

## Rationale

### `main`

| Rule                                                          | Setting                                                  | Why                                                                                                                                                                                                                                                                                                |
| ------------------------------------------------------------- | -------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Target                                                        | `~DEFAULT_BRANCH` and `refs/heads/main`                  | Follows a rename of the default branch, and keeps `main` covered if the default ever changes.                                                                                                                                                                                                      |
| `deletion`                                                    | on                                                       | `main` can't be deleted.                                                                                                                                                                                                                                                                           |
| `non_fast_forward`                                            | on                                                       | No force-push or history rewrite.                                                                                                                                                                                                                                                                  |
| `required_signatures`                                         | on                                                       | Already 100% true in practice. It applies to every commit in a PR's head, not only the merge commit, so an unsigned commit anywhere in a stack blocks the final merge into `main`.                                                                                                                 |
| `pull_request`                                                | on                                                       | Every change reaches `main` through a PR, and direct pushes are refused. The PR is the user's merge gate.                                                                                                                                                                                          |
| `required_approving_review_count`                             | `0`                                                      | GitHub doesn't let an author approve their own PR. Agents push as the only human, so a value of 1 or more would make every PR unmergeable.                                                                                                                                                         |
| Last-push approval, stale-review dismissal, code-owner review | off                                                      | These only matter when approvals are required.                                                                                                                                                                                                                                                     |
| `required_review_thread_resolution`                           | on                                                       | Unresolved review threads block the merge, so every comment is answered or resolved first. That includes bot and Copilot threads, which the user resolves deliberately.                                                                                                                            |
| `allowed_merge_methods`                                       | `["merge"]`                                              | Matches how PRs are merged today. When a parent PR merges with a merge commit, the retargeted child's diff stays clean. Squash or rebase rewrites the parent's commits, so the child shows them again and conflicts. GitHub signs its own merge commits, so this works with `required_signatures`. |
| `required_linear_history`                                     | absent, **deliberately**                                 | Linear history forbids merge commits, and merge commits are the only allowed method. The user first asked for linear history, then dropped it once this conflict came up. **Don't add it.** Merge commits are what keep stacked PRs working.                                                       |
| `required_status_checks`                                      | absent until CI exists, then `ci-ok` with `strict: true` | A required check that never reports blocks every PR forever, so the rule is added only once `ci-ok` reports. Its desired form, including the up-to-date requirement, is in [Future CI](#future-ci).                                                                                                |
| `bypass_actors`                                               | `[]`                                                     | The normal flow (0 approvals, no checks) never needs a bypass. Even a PR-only admin bypass is unsafe here. Agents act as the admin, so an agent could run `gh pr merge --admin --rebase` and land rebased commits on `main` that may be unsigned, skipping `required_signatures`.                  |

Having no bypass can't lock the owner out. Editing, disabling, or deleting a ruleset is a
repo-admin permission and doesn't depend on bypass. The escape hatch is the
[emergency path](#emergency-path). The REST spec also allows a `User` bypass actor; it isn't used,
for the same reason.

### `release-tags`

| Rule                                              | Why                                                                                                                                                                                                                                                                                                                                                                                     |
| ------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `deletion`                                        | A published `v*` tag can't be removed.                                                                                                                                                                                                                                                                                                                                                  |
| `update` (`update_allows_fetch_and_merge: false`) | A published `v*` tag can't be moved to another commit.                                                                                                                                                                                                                                                                                                                                  |
| `non_fast_forward`                                | An extra guard against force-moving a tag. Harmless next to `update`.                                                                                                                                                                                                                                                                                                                   |
| `creation` left open                              | Restricting creation only works with a bypass actor to create tags. Bypass covers the whole ruleset, not one rule, so a bypass actor could also delete and move tags. The owner and the agents are the same admin, so that would remove immutability for exactly the actors it guards against. Leaving creation open also lets a future release workflow on `GITHUB_TOKEN` create tags. |
| `bypass_actors: []`                               | Tags are truly immutable. To fix a bad tag, use the [emergency path](#emergency-path).                                                                                                                                                                                                                                                                                                  |

Only the `v*` pattern is used. No tags exist yet, and a narrower pattern such as
`v[0-9]*` buys nothing until a release scheme exists.

### Merge settings

The `main` ruleset only governs merges into `main`. A child PR merged into its parent branch
inside a stack isn't covered by any ruleset, because feature branches are deliberately
unprotected. Turning squash and rebase off for the whole repo keeps those merges
merge-commit-only too, so no rewritten or unsigned commits enter a stack through the merge
button.

`allow_update_branch` is on because the required-checks rule will be strict (branches must be up
to date with `main` before merging), and the "Update branch" button is how a PR catches up.
Use its "Update with merge commit" option; see [Rules for agents](#rules-for-agents).

### Feature branches: deliberately unprotected

Agents force-push stacked branches after rebasing them onto an updated parent, and merged
branches are deleted automatically. `non_fast_forward` or `deletion` on `feat/*` or `chore/*`
would break that workflow. Requiring signatures on every branch was also considered. It was
left out because signing is already enforced at the only point that matters, the merge into
`main`.

## Rules for agents

- **Merging.** Merge a PR only when the user asks in the current session, and then only with
  `gh pr merge <n> --merge`. Never use `--admin`, `--squash`, or `--rebase`.
- **Settings.** Change rulesets and repo settings only through
  [`apply-repo-rules`](../../skills/apply-repo-rules/SKILL.md). Its `apply` subcommand applies
  `rules.md` from `origin/main` and needs no further approval, because the user's merge is the
  approval. Applying from any other ref (`apply-ref`) needs the user's explicit approval in the
  current session, and so does every other ruleset or repo-setting change, including the
  [emergency path](#emergency-path) and [roll back](#roll-back).
- **Updating a PR branch from its base.** Prefer the "Update with merge commit" button, or a local
  signed rebase (`git rebase` with `commit.gpgsign` on) followed by a force-push of the feature
  branch. Avoid "Update with rebase". It hasn't been verified, but its rebased commits may be
  unsigned, and `required_signatures` would then block the stack's eventual merge into `main`.
- **Pushing.** Never push to `main`. Never force-push, move, or delete a `v*` tag. Sign every
  commit (`--gpg-sign`).
- **Keeping this file current.** Change `rules.md` and this spec together in a PR, and apply
  after the user merges it.

## Procedures

All of these use `gh` authenticated as the owner. The user allowlists the
[`apply-repo-rules`](../../skills/apply-repo-rules/SKILL.md) commands in the agent host, and its
Host setup section lists the rules. Agents run nothing else against these settings without the
user's approval (see [Rules for agents](#rules-for-agents)). If the host denies a command, stop,
report it, and let the user decide. Don't work around the denial.

### Apply

From the repository root:

```sh
share/skills/apply-repo-rules/apply-repo-rules.sh apply
```

It fetches `origin/main` and reads `rules.md` there. Then it creates missing rulesets, `PUT`s
any that differ (looked up by name, since a `POST` with a taken name creates a duplicate or
fails), `PATCH`es merge settings that differ, and runs the [drift check](#check-for-drift). It
never deletes a ruleset. `apply-ref <ref>` does the same from another ref, and needs the user's
approval every time.

After applying, confirm that open PRs targeting `main` are still mergeable:

```sh
gh pr list --base main --state open --json number \
  --jq '.[].number' | xargs -I{} gh pr view {} --json number,mergeable,mergeStateStatus
```

### Check for drift

This is read-only, so agents may run it at any time:

```sh
share/skills/apply-repo-rules/apply-repo-rules.sh check        # against rules.md on origin/main
share/skills/apply-repo-rules/apply-repo-rules.sh check HEAD   # against a PR branch's rules.md
```

It prints `OK` or `FAIL` for each ruleset and for the repo settings, with a diff for each
`FAIL`, and exits 1 on drift. It compares only the keys a payload sets, because a `GET` adds
server fields such as `id` and `_links`. It looks rulesets up by name, because IDs aren't fixed.
A live ruleset that `rules.md` doesn't list is drift too.

The live API can return extra fields inside a rule. For example, a `pull_request` rule can gain
newer parameters with default values. If the only differences are new defaulted fields, add them
to `rules.md` rather than treating them as drift.

### Emergency path

Use this for something no rule allows, such as a hotfix pushed directly to `main` or re-pointing
a bad tag. It needs the user's go-ahead every time.

1. Find the ruleset's id:
   `gh api repos/bryant-finney/budge/rulesets --jq '.[] | {id, name}'`.
2. Disable it:
   `gh api --method PUT repos/bryant-finney/budge/rulesets/<id> -f enforcement=disabled`.
3. Do the one thing that needed it.
4. Turn it back on:
   `gh api --method PUT repos/bryant-finney/budge/rulesets/<id> -f enforcement=active`.
5. Run the [drift check](#check-for-drift) and confirm everything is `OK`. If you skip step 4,
   the next `apply` turns enforcement back on.

### Roll back

To remove a ruleset entirely, run
`gh api --method DELETE repos/bryant-finney/budge/rulesets/<id>`. To soften it without losing it,
use step 2 of the [emergency path](#emergency-path) and leave it disabled. To restore the old
merge settings, run
`gh api -X PATCH repos/bryant-finney/budge -F allow_squash_merge=true -F allow_rebase_merge=true -F allow_update_branch=false`.
Update `rules.md` and this spec in the same change, or the next `apply` reverts the rollback (it
never deletes a ruleset, but it re-enables a disabled one and restores merge settings).

## Limits

These rules stop **accidents**: a mistaken push to `main`, a force-push, a deleted branch or tag,
or a squash or rebase merge that breaks a stack. They **don't stop a misbehaving agent**,
because agents act as the admin:

- Agents share the owner's admin identity and GPG key, so their commits are signed and verified
  like the owner's.
- With 0 approvals required (and, once CI lands, only a green `ci-ok`), an agent can open a PR
  and merge it itself.
- An agent holding admin credentials can `PUT` or `DELETE` the rulesets and `PATCH` repo
  settings.

The real controls sit outside GitHub.

- **Agent permission deny-rules** (in Claude Code settings; only the user changes them). Narrow
  each rule to `main` and tags where the matcher allows it, because a blanket force-push deny
  would also block normal rebases of stacked feature branches.
  - `Bash(gh pr merge:*)`: only the user merges, unless the user asks in the current session.
  - `gh api` with `--method`/`-X` `POST`, `PUT`, `PATCH`, or `DELETE` on `repos/*/rulesets*`,
    on `repos/bryant-finney/budge` itself (repo settings), and on `repos/*/git/refs*`.
  - `Bash(git push origin main:*)`, `Bash(git push --tags:*)`, `Bash(git push origin v*:*)`,
    `Bash(git push --delete:*)`, and `Bash(git tag -d:*)`.
- **A separate non-admin agent identity** (longer term): a machine user with write access, or a
  GitHub App. With that, `required_approving_review_count: 1` becomes workable, and agents can
  no longer edit rulesets.

### Public-repo access

- Outside users get read access only. They can open PRs from forks, but they can't push here or
  merge anything. Merging needs write access.
- `required_approving_review_count: 0` only affects accounts with write access, which today means
  only the owner. **When a write collaborator is added, raise it to 1** so nobody else can merge
  their own PR unreviewed.
- Audit GitHub Apps that have `contents: write`, because an app with write access can push past
  anything a bypass list doesn't name. There is a `copilot` environment, so check what the
  Copilot app is allowed to do. This read-only listing shows what's installed:
  `gh api user/installations --jq '.installations[] | {app_slug, permissions}'`.
- Workflows (once they exist): never use `pull_request_target` to check out or run fork code
  with secrets. Set Actions to **require approval for all outside contributors** before workflows
  run on their PRs.

## Future CI

When PR workflows land (issue #15), add the required checks to the `main` ruleset.

**Trigger.** Don't put a `branches:` filter on `on.pull_request`. Stacked PRs target feature
branches first and are retargeted to `main` when the parent merges. With `branches: [main]` the
checks never run for those heads, so the required check never reports. Include `edited` so that
a base change re-runs the checks:

```yaml
on:
  pull_request:
    types: [opened, synchronize, reopened, edited]
```

**Rule (desired state once CI exists).** Once `ci-ok` has reported at least once on a PR, add
these rows to the `main` Rule table in `rules.md`, merge the PR, and run [Apply](#apply).

| Rule                     | Parameter                              | Value                                             |
| ------------------------ | -------------------------------------- | ------------------------------------------------- |
| `required_status_checks` | `strict_required_status_checks_policy` | `true`                                            |
| `required_status_checks` | `do_not_enforce_on_create`             | `false`                                           |
| `required_status_checks` | `required_status_checks`               | `[{"context": "ci-ok", "integration_id": 15368}]` |

- `context` must exactly match the job's check-run name, as reported by
  `gh api repos/bryant-finney/budge/commits/<sha>/check-runs --jq '.check_runs[].name'`.
  Require one aggregating job (`ci-ok`) rather than each matrix leg, so adding a Python version
  doesn't change the ruleset.
- `integration_id: 15368` is the GitHub Actions app. It stops another app from reporting a
  spoofed `ci-ok`.
- `strict_required_status_checks_policy: true` is required: a PR must be up to date with `main`
  before it merges, so `ci-ok` has run against what will actually land. The accepted cost is
  churn: each merge into `main` makes every other open PR targeting `main` stale, and each one
  needs "Update with merge commit" (and a fresh `ci-ok`) before it can merge. A stacked child
  retargeted to `main` needs the same update.
- **Never add the GitHub Actions app, or any workflow token, as a bypass actor.** Any workflow
  run, including one triggered by a PR, could then push past the rules.

## Relationship to issue #17

Issue #17 (repo settings as code) was first written while the repo was private, and its ruleset
and merge sections (2 and 3) disagreed with this spec. The user settled those conflicts on
2026-10-17, and #17 was updated to match and to point here as the source of truth. These
decisions overrode #17's original text, which is why they're recorded here:

| Topic                     | Original #17 | Settled                            |
| ------------------------- | ------------ | ---------------------------------- |
| Merge method              | squash only  | merge commits only                 |
| `required_linear_history` | on           | off (conflicts with merge commits) |

The rest of #17 is out of scope here: CODEOWNERS, Actions permissions, security settings, labels,
and the `repo-settings.sh` verification script. When that script lands, it should read rulesets
and merge settings from `rules.md` (through `parse-rules.jq`) rather than keep a second copy that
can drift apart.
