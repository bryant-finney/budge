---
name: git-commit-hook-gotchas
description: budge's prepare-commit-msg hook prepends `<type>(#<issue>):` from the branch name on every commit, amend included; omit the prefix, set GIT_SKIP_OWNER_NAME=1, never commit with an empty message
metadata:
  type: feedback
---

# Commit hook prefix

The local `prepare-commit-msg` hook (`.git/hooks/prepare-commit-msg`, shared by every worktree)
always prepends a prefix derived from the branch name, and it doesn't check whether the message
already has one. On `feat/13/...` with `GIT_SKIP_OWNER_NAME=1`, that prefix is `feat(#13):` plus a
space. Without the variable the issue part becomes `<owner>/<repo>#13`, guessed from the path (in
the `pr-22` worktree it came out as `worktrees/pr-22#14`). Write only the subject:
`GIT_SKIP_OWNER_NAME=1 git commit --signoff --gpg-sign -m "accept current IANA zone names"`.

**Why:** in PR #21 (2026-10-18), two commits were written with the full `feat(#13): ...` subject.
The hook doubled it (`feat(#13): feat(#13): ...`), and they were pushed before anyone noticed.
Fixing a pushed subject takes a force-push, plus a restack of any PR stacked on the branch. That
needs the user's go-ahead, so get the subject right before pushing.

**How to apply:** before every commit on a `<type>/<issue>/...` branch, leave the prefix out of
the message. Check `git log -1 --format=%s` before pushing. For a different type than the branch
gives (e.g. `test` on a `feat/` branch), disable the hook temporarily, as the user's global
instructions describe.

## Related hook behavior

- **Empty message:** the hook fills one in from whatthecommit.com. Always pass a message.
- **`git commit --amend` runs the hook again.** On 2026-10-18, `--amend --no-edit` without
  `GIT_SKIP_OWNER_NAME=1` gave `chore(worktrees/pr-22#14): chore(#14): ...`. Amend with
  `GIT_SKIP_OWNER_NAME=1 git commit --amend --signoff --gpg-sign -F <file>`, where the file holds
  the bare subject plus trailers, then check `git log -1 --format=%B`. Leaving out `--signoff` on
  an amend drops the `Signed-off-by` trailer.
- **`fatal: ref HEAD is not a symbolic ref` during a rebase is harmless.** The hook runs on the
  detached HEAD, can't read the branch, and adds no prefix, so each picked commit keeps its
  original message. Confirm with `git range-diff`.

Related: [[git-worktree-restack]].
