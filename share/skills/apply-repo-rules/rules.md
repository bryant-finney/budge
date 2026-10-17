# Repo rules

This is the desired state of the rulesets and merge settings on `bryant-finney/budge`.
[`apply-repo-rules.sh`](apply-repo-rules.sh) reads these tables, and the
[repo protection spec](../../agents/infra/repo-protection.md) explains each choice. Change this
file and the spec's rationale together, in one PR.

## Format

- `## Ruleset <name>` starts a ruleset. Its **Setting** table sets `target` (`branch` or `tag`),
  `enforcement`, and the `include` and `exclude` ref patterns. A list is a comma-separated run of
  code spans, and `none` means an empty list.
- Its **Rule** table has one row per rule parameter. A rule with no parameters gets one row with
  empty Parameter and Value cells.
- Its optional **Bypass** table has one row per bypass actor: the actor type, the actor ID, and
  the bypass mode (`always`, `pull_request`, or `exempt`). `RepositoryRole` `5` is the repository
  admin role, which on this personal-account repo means the owner. Without the table, nobody can
  bypass the ruleset.
- `## Repository settings` lists repo fields set with `PATCH /repos/{owner}/{repo}`.
- A value is a code span. It is read as JSON when it parses (`0`, `false`, `["merge"]`), and as a
  string otherwise.
- The unlabeled first column is ✅ when the value is `true` or `active`, ❌ when it's `false`, and blank
  otherwise. The parser rejects a row whose mark doesn't match its value.
- The parser ignores every other heading, so prose can go between sections.

## Ruleset `main`

|     | Setting       | Value                                |
| --- | ------------- | ------------------------------------ |
|     | `target`      | `branch`                             |
| ✅  | `enforcement` | `active`                             |
|     | `include`     | `~DEFAULT_BRANCH`, `refs/heads/main` |
|     | `exclude`     | none                                 |

|     | Rule                  | Parameter                           | Value       |
| --- | --------------------- | ----------------------------------- | ----------- |
|     | `deletion`            |                                     |             |
|     | `non_fast_forward`    |                                     |             |
|     | `required_signatures` |                                     |             |
|     | `pull_request`        | `allowed_merge_methods`             | `["merge"]` |
| ❌  | `pull_request`        | `dismiss_stale_reviews_on_push`     | `false`     |
| ✅  | `pull_request`        | `require_code_owner_review`         | `true`      |
| ✅  | `pull_request`        | `require_last_push_approval`        | `true`      |
|     | `pull_request`        | `required_approving_review_count`   | `0`         |
| ✅  | `pull_request`        | `required_review_thread_resolution` | `true`      |

|     | Bypass           | Actor ID | Mode     |
| --- | ---------------- | -------- | -------- |
|     | `RepositoryRole` | `5`      | `always` |

## Ruleset `release-tags`

|     | Setting       | Value          |
| --- | ------------- | -------------- |
|     | `target`      | `tag`          |
| ✅  | `enforcement` | `active`       |
|     | `include`     | `refs/tags/v*` |
|     | `exclude`     | none           |

|     | Rule               | Parameter                       | Value   |
| --- | ------------------ | ------------------------------- | ------- |
|     | `deletion`         |                                 |         |
|     | `non_fast_forward` |                                 |         |
| ❌  | `update`           | `update_allows_fetch_and_merge` | `false` |

|     | Bypass           | Actor ID | Mode     |
| --- | ---------------- | -------- | -------- |
|     | `RepositoryRole` | `5`      | `always` |

## Repository settings

|     | Setting               | Value   |
| --- | --------------------- | ------- |
| ✅  | `allow_merge_commit`  | `true`  |
| ❌  | `allow_squash_merge`  | `false` |
| ❌  | `allow_rebase_merge`  | `false` |
| ✅  | `allow_update_branch` | `true`  |
