---
name: git-commit-hook-gotchas
description: budge's prepare-commit-msg hook always prepends `<type>(#<issue>):` from the branch name, so commit messages must omit the prefix
metadata:
  type: feedback
---

# Commit hook prefix

The local `prepare-commit-msg` hook (`.git/hooks/prepare-commit-msg`, shared by every worktree)
always prepends a prefix derived from the branch name. On `feat/13/...` with
`GIT_SKIP_OWNER_NAME=1`, that prefix is `feat(#13):` plus a space. Write only the subject, e.g.
`git commit -m "accept current IANA zone names"`.

**Why:** in PR #21 (2026-10-18), two commits were written with the full `feat(#13): ...` subject.
The hook doubled it (`feat(#13): feat(#13): ...`), and they were pushed before anyone noticed.
Fixing a pushed subject takes a force-push, plus a restack of any PR stacked on the branch. That
needs the user's go-ahead, so get the subject right before pushing.

**How to apply:** before every commit on a `<type>/<issue>/...` branch, leave the prefix out of
the message. Check `git log -1 --format=%s` before pushing. For a different type than the branch
gives (e.g. `test` on a `feat/` branch), disable the hook temporarily, as the user's global
instructions describe.
