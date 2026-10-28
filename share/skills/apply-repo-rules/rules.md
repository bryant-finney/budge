# Repo rules

This is the desired state of the rulesets and merge settings on `bryant-finney/budge`, and why.
[`apply-repo-rules.sh`](apply-repo-rules.sh) reads these tables. Change a table and its "Why" notes
together.

## Context

- One human, `bryant-finney` (repo admin). Agents run as that account with the same GPG key, so
  GitHub can't tell them apart from the owner. These rules stop accidents by anyone without the
  bypass. The owner's bypass on ruleset `main` is `always`, so for the owner's account, agents
  included, that ruleset stops nothing on `main`; only the agents' instructions do. Ruleset
  `main-history` has no bypass, so nobody can force-push or delete `main`.
- Agents open stacked PRs. When a parent merges, GitHub deletes its head branch
  (`delete_branch_on_merge`) and so retargets the child to `main`.
- Feature branches and non-`v*` tags are deliberately unprotected: agents force-push rebased
  stacks, and signing is required at the merge into `main`, except through the owner's bypass.

## Format

- `## Ruleset <name>` starts a ruleset. Its **Setting** table sets `target` (`branch` or `tag`),
  `enforcement`, and the `include` and `exclude` ref patterns. A list is a comma-separated run of
  code spans, and `none` means an empty list.
- Its **Rule** table has one row per rule parameter. A rule with no parameters gets one row with
  empty Parameter and Value cells.
- Its optional **Bypass** table has one row per bypass actor: the actor type, the actor ID, and
  the bypass mode (`always`, `pull_request`, or `exempt`; `pull_request` applies only to branch
  rulesets). `RepositoryRole` `5` is the repository admin role, which on this personal-account
  repo means the owner. Without the table, nobody can bypass the ruleset.
- `## Repository settings` lists repo fields set with `PATCH /repos/{owner}/{repo}`.
- A value is a code span. It is read as JSON when it parses (`0`, `false`, `["merge"]`), and as a
  string otherwise.
- The unlabeled first column is ✅ when the value is `true` or `active`, ❌ when it's `false`, and blank
  otherwise. The parser rejects a row whose mark doesn't match its value.
- The parser ignores every other heading and any line outside a table, so prose can go anywhere.

## Ruleset `main`

|     | Setting       | Value                                |
| --- | ------------- | ------------------------------------ |
|     | `target`      | `branch`                             |
| ✅  | `enforcement` | `active`                             |
|     | `include`     | `~DEFAULT_BRANCH`, `refs/heads/main` |
|     | `exclude`     | none                                 |

|     | Rule                     | Parameter                              | Value                                          |
| --- | ------------------------ | -------------------------------------- | ---------------------------------------------- |
|     | `deletion`               |                                        |                                                |
|     | `non_fast_forward`       |                                        |                                                |
|     | `required_signatures`    |                                        |                                                |
|     | `pull_request`           | `allowed_merge_methods`                | `["merge"]`                                    |
| ❌  | `pull_request`           | `dismiss_stale_reviews_on_push`        | `false`                                        |
| ✅  | `pull_request`           | `require_code_owner_review`            | `true`                                         |
| ✅  | `pull_request`           | `require_last_push_approval`           | `true`                                         |
|     | `pull_request`           | `required_approving_review_count`      | `0`                                            |
| ✅  | `pull_request`           | `required_review_thread_resolution`    | `true`                                         |
|     | `required_status_checks` | `required_status_checks`               | `[{"context":"ci-ok","integration_id":15368}]` |
| ✅  | `required_status_checks` | `strict_required_status_checks_policy` | `true`                                         |
| ❌  | `required_status_checks` | `do_not_enforce_on_create`             | `false`                                        |

|     | Bypass           | Actor ID | Mode     |
| --- | ---------------- | -------- | -------- |
|     | `RepositoryRole` | `5`      | `always` |

Why:

- **Require `ci-ok` only.** The `ci-ok` job in `.github/workflows/ci.yml` needs every other CI
  job and fails unless each one succeeded, so one context from GitHub Actions (integration
  `15368`) covers `pre-commit` and every `test` matrix entry. Requiring the matrix contexts
  directly (`test (python, 3.12)`, ...) would mean editing this table with every matrix change,
  and a context that no longer reports would leave every PR pending. `ci-ok` runs `if: always()`
  because GitHub counts a skipped required check as passing; it treats a skipped, cancelled, or
  failed job as failure. Keep it that way: add new jobs to its `needs`, and never give it a
  `name:` (that renames the context), a path filter, or a skip condition. Apply these rules only
  after the workflow and this desired state merge to `main` and `ci-ok` has reported there.
- **Merge commits only.** Squash or rebase rewrites a parent's commits, so the retargeted child
  shows them again and conflicts. No `required_linear_history`, deliberately: it forbids merge
  commits.
- **`required_approving_review_count: 0`.** An author can't approve their own PR, and the only
  human authors every PR. Raise it to 1 when a write collaborator is added.
- **`require_code_owner_review`.** CODEOWNERS gives every path to `@bryant-finney` alone, so every
  PR merges **only through the owner's admin bypass**. The owner accepted this (2026-10-17).
- **`require_last_push_approval`.** GitHub doesn't document it with 0 approvals. If it blocks PRs,
  the bypass still merges them. After an `apply`, confirm open PRs are still mergeable.
- **Bypass `always`.** The owner can bypass-merge PRs and can also push directly to `main`. The
  owner switched from `pull_request` mode in the web UI (2026-10-17) after that mode rejected a
  direct push of `2a5f0cd`, as designed: `pull_request` mode only bypasses rules when merging a
  PR. The bypass covers every rule in this ruleset, so the owner, and any agent running as the
  owner, can also push unsigned commits. Force-pushing and deleting `main` stay blocked by
  ruleset `main-history`. Agents must not push to `main`: the "Merging and pushing" rule in each
  agent's `AGENT.md` (`b-end`, `f-end`, and `infra`) forbids it and anything that works only
  because of the bypass. A session that loads none of those agents has no such guard. To enforce
  it again, change the Bypass mode above to `pull_request` in a PR and run `apply` after it
  merges; then a hotfix goes through a PR.
- **Never add GitHub Actions or a workflow token as a bypass actor.**

## Ruleset `main-history`

|     | Setting       | Value                                |
| --- | ------------- | ------------------------------------ |
|     | `target`      | `branch`                             |
| ✅  | `enforcement` | `active`                             |
|     | `include`     | `~DEFAULT_BRANCH`, `refs/heads/main` |
|     | `exclude`     | none                                 |

|     | Rule               | Parameter | Value |
| --- | ------------------ | --------- | ----- |
|     | `deletion`         |           |       |
|     | `non_fast_forward` |           |       |

Why:

- **No Bypass table, deliberately.** Nobody, the owner included, can force-push or delete `main`;
  GitHub rejects the push. Never add a bypass actor: that's the one thing this ruleset exists to
  prevent. The owner can still disable or delete the ruleset itself (the emergency path in
  [`SKILL.md`](SKILL.md), or the web UI). `check` reports either as drift, and `apply` re-enables a
  disabled ruleset and recreates a deleted one.
- **Separate from ruleset `main`.** Bypass actors belong to one ruleset, and GitHub enforces the
  rules of every ruleset that targets a branch, so `main`'s `always` bypass doesn't reach these
  rules. `deletion` and `non_fast_forward` stay in ruleset `main` too, so adding this ruleset
  doesn't change that one.

## Ruleset `release-tags`

|     | Setting       | Value          |
| --- | ------------- | -------------- |
|     | `target`      | `tag`          |
| ✅  | `enforcement` | `active`       |
|     | `include`     | `refs/tags/v*` |
|     | `exclude`     | none           |

|     | Rule               | Parameter | Value |
| --- | ------------------ | --------- | ----- |
|     | `deletion`         |           |       |
|     | `non_fast_forward` |           |       |
|     | `update`           |           |       |

|     | Bypass           | Actor ID | Mode     |
| --- | ---------------- | -------- | -------- |
|     | `RepositoryRole` | `5`      | `always` |

Why:

- **Bypass `always`.** `pull_request` mode exists only for branch rulesets. The owner can re-point
  or delete a bad tag directly.
- **`update` without parameters.** `update_allows_fetch_and_merge` defaults to `false`, and the
  live ruleset doesn't store it. A row pinning `false` made `check` report drift that the live
  settings can't match, so don't add that row back. The cost: `check` doesn't compare this
  parameter. If it's ever set to `true` live, `check` still reports `OK`, with only a
  `NOTE ... not in rules.md, so not compared`.
- **Tag `creation` left open.** Restricting it would leave only the admin able to tag, and would
  block a future release workflow on `GITHUB_TOKEN`.

## Repository settings

|     | Setting                  | Value   |
| --- | ------------------------ | ------- |
| ✅  | `allow_merge_commit`     | `true`  |
| ❌  | `allow_squash_merge`     | `false` |
| ❌  | `allow_rebase_merge`     | `false` |
| ✅  | `allow_update_branch`    | `true`  |
| ✅  | `delete_branch_on_merge` | `true`  |

Why:

- **Squash and rebase off repo-wide.** This also covers merges between stacked branches, which no
  ruleset governs.
- **`allow_update_branch`.** Use "Update with merge commit", not "Update with rebase", whose
  commits may be unsigned and then fail `required_signatures`.
