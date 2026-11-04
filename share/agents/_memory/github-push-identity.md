---
name: github-push-identity
description: Every agent push authenticates as bryant-finney-bot; select its gh token over HTTPS and verify the recorded push actor independently of commit signing.
metadata:
  type: feedback
---

# Push as the bot

Every agent-initiated push to `bryant-finney/budge` must authenticate as `bryant-finney-bot`.
This includes ordinary pushes and authorized pushes with `--force-with-lease`. Keep the existing
restrictions on `main`, protected tags, and history rewrites.

Commit author, committer, and signing key do not determine the Git transport's account.
`gh api user` alone does not establish the account used by `git push origin`: this checkout's
`origin` uses SSH, whose identity is selected separately. Prefer the account-pinned HTTPS
recipe below; it needs no SSH configuration or second remote.

## Select and verify credentials for each push

Run from the intended PR worktree. The subshell confines the token to this operation and
selects the bot even if another account is active in `gh`. Never print the token, put it in a
remote URL or file, or enable shell tracing around these commands. Stop if token retrieval or
identity verification fails.

```bash
(
  GH_TOKEN="$(gh auth token --hostname github.com --user bryant-finney-bot)" || exit
  export GH_TOKEN
  test "$(gh api --hostname github.com user --jq .login)" = bryant-finney-bot || exit 1
  test "$(git ls-remote --get-url https://github.com/bryant-finney/budge.git)" = \
    https://github.com/bryant-finney/budge.git || exit 1
  budge_branch="$(git branch --show-current)" || exit
  test -n "$budge_branch" && test "$budge_branch" != main || exit 1
  GIT_TERMINAL_PROMPT=0 git \
    -c credential.helper= \
    -c 'credential.helper=!gh auth git-credential' \
    -c http.https://github.com/.extraheader= \
    push https://github.com/bryant-finney/budge.git "HEAD:refs/heads/$budge_branch"
)
```

The empty credential-helper setting clears inherited helpers; the next setting uses the
explicitly selected bot token. The empty GitHub extra-header setting clears an inherited
authorization header. The URL check rejects an SSH rewrite instead of silently using its key.
For an authorized history rewrite, add an explicit
`--force-with-lease=refs/heads/BRANCH:OLD_SHA` to this same `push` command. Use the same verified
credentials for every other authorized ref update; do not fall back to a bare push to `origin`.

## Verify the server-side actor

Confirm the remote branch tip equals the intended local SHA. Then query the repository
activity API for that branch and SHA and require `actor.login == "bryant-finney-bot"`:

```text
GET /repos/bryant-finney/budge/activity?ref=refs/heads/BRANCH&activity_type=push&per_page=100
```

Paginate if needed and match the activity's `after` SHA; activity can lag the push. Commit
signature verification is a separate check and is not evidence of the push account.

## Last reviewable push

On PR #56 (2026-11-03), an empty bot push restarted CI but left GitHub's last-reviewable-push
blocker naming the owner. A small documentation change pushed by the bot changed the blocker
to a request for reapproval of the latest content. Verify the recorded actor and content diff
before treating an empty commit as a fix. The owner's review must satisfy GitHub's current
requirements after the latest reviewable change.

References: [account-specific gh tokens](https://cli.github.com/manual/gh_auth_token),
[GitHub's review requirements](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches),
and [PR #56](https://github.com/bryant-finney/budge/pull/56).
