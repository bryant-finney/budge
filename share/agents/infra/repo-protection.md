# Repository protection spec

Why `bryant-finney/budge` is protected the way it is. The desired state is
[`rules.md`](../../skills/apply-repo-rules/rules.md), and the
[`apply-repo-rules`](../../skills/apply-repo-rules/SKILL.md) skill checks and applies it. infra
owns all three. Change `rules.md` and this file together, in one PR.

## Context

- One human, `bryant-finney` (repo admin). Agents run as that account with the same GPG key, so
  GitHub can't tell them apart from the owner.
- Agents open stacked PRs. When a parent merges, GitHub deletes its head branch
  (`delete_branch_on_merge`) and so retargets the child to `main`.
- Feature branches and non-`v*` tags are deliberately unprotected: agents force-push rebased
  stacks, and signing is enforced where it matters, at the merge into `main`.

## Rationale for non-obvious rules

- **Merge commits only** (`allowed_merge_methods`, and squash/rebase off repo-wide). Squash or
  rebase rewrites a parent's commits, so the retargeted child shows them again and conflicts.
  Repo-wide, it also covers merges between stacked branches, which no ruleset governs.
- **No `required_linear_history`, deliberately.** It forbids merge commits. Don't add it.
- **`required_approving_review_count: 0`.** An author can't approve their own PR, and the only
  human authors every PR. Raise it to 1 when a write collaborator is added.
- **`require_code_owner_review`.** CODEOWNERS gives every path to `@bryant-finney` alone, so
  nobody can approve, and every PR merges **only through the owner's admin bypass**. The owner
  accepted this (2026-10-17): bypass merges are the normal path, not an emergency.
- **`require_last_push_approval`.** GitHub doesn't document it with 0 approvals. If it blocks PRs,
  the bypass still merges them. After an `apply`, confirm open PRs are still mergeable.
- **`main` bypass: admin, `pull_request` mode.** The owner can bypass-merge PRs, but nobody,
  agents included, can push to, force-push, or delete `main`. A hotfix goes through a PR. Cost:
  agents can bypass-merge too (`gh pr merge --admin`), which only the rules below stop.
- **`release-tags` bypass: admin, `always`.** `pull_request` mode exists only for branch
  rulesets. The owner can re-point or delete a bad tag directly.
- **Tag `creation` left open.** Restricting it would leave only the admin able to tag, and would
  block a future release workflow on `GITHUB_TOKEN`.
- **`allow_update_branch`.** Use "Update with merge commit", not "Update with rebase", whose
  commits may be unsigned and then fail `required_signatures`.

## Rules for agents

- **Never merge into `main`.** Every merge needs the bypass, which is the owner's alone. Report
  that the owner must merge (UI, or `gh pr merge <n> --merge --admin` run by the user). Never run
  `--admin`, `--squash`, or `--rebase`.
- **Never push to `main`.** Never force-push, move, or delete a `v*` tag. Sign every commit.
- **Never do anything that works only because of the bypass**, even when GitHub allows it.
- **Change settings only through `apply-repo-rules`.** `apply` from `main` needs no approval,
  because the owner's merge is the approval. Everything else (`apply-ref`, the emergency path,
  any direct `gh api` write) needs the user's approval in the current session. If the host denies
  a command, stop and report it.

## Emergency path

Only for when a ruleset must be off for everyone. It needs the user's go-ahead every time.

1. Disable the ruleset: `PUT repos/bryant-finney/budge/rulesets/<id>` with
   `enforcement=disabled`.
2. Do the one thing that needed it.
3. Re-enable it (`enforcement=active`), then run `check` and confirm `OK`. The next `apply`
   re-enables it anyway.

To roll back for good, change `rules.md` in a PR as well: `apply` never deletes a ruleset, but it
re-enables disabled ones and restores merge settings.

## Limits

These rules stop **accidents**, not a misbehaving agent, because agents act as the admin:

- An agent can bypass-merge, move a tag, and `PUT`/`DELETE` rulesets or `PATCH` settings.
- `apply` refuses to run unless the skill on disk matches `main`, but an edited script can drop
  that check.

The real controls sit outside GitHub:

- **Deny-rules in agent settings** (only the user edits them): `Bash(gh pr merge:*)` matters
  most, because an agent's bypass merge looks like the owner's. Also deny `gh api` writes to
  `repos/*/rulesets*`, `repos/bryant-finney/budge`, and `repos/*/git/refs*`, and tag pushes and
  deletes. Keep force-push denies narrow, or they block stacked-branch rebases.
- **Longer term, a non-admin agent identity** (machine user or GitHub App), which makes 1
  required approval workable and takes ruleset edits away from agents.
- **Public repo.** Audit apps with `contents: write`, including Copilot. Workflows must never run
  fork code with secrets through `pull_request_target`, and outside contributors' workflow runs
  need approval.

## Future CI

When PR workflows land (issue #15):

- Don't filter `on.pull_request` by `branches:`, or stacked PRs never report the check. Include
  `edited` in `types` so a retarget re-runs it.
- Once `ci-ok` has reported on a PR, add these rows to the `main` Rule table:

|     | Rule                     | Parameter                              | Value                                             |
| --- | ------------------------ | -------------------------------------- | ------------------------------------------------- |
| ✅  | `required_status_checks` | `strict_required_status_checks_policy` | `true`                                            |
| ❌  | `required_status_checks` | `do_not_enforce_on_create`             | `false`                                           |
|     | `required_status_checks` | `required_status_checks`               | `[{"context": "ci-ok", "integration_id": 15368}]` |

- `ci-ok` is one aggregating job, so the matrix can change without a ruleset change.
  `integration_id` `15368` (GitHub Actions) stops other apps from spoofing it. Strict mode means
  each merge into `main` makes other open PRs stale until they update.
- Never add GitHub Actions or a workflow token as a bypass actor.
