---
name: gh-commit-skill-forks
description: the gh:commit skill runs as a background agent that stages and commits by itself; wait for its notification instead of committing in parallel
metadata:
  type: feedback
---

# gh:commit runs as a background agent

Invoking `gh:commit` launches a background `gh-commit` agent that stages the changes, writes the message, and makes
the signed commit itself. Its footer adds a `Generated with [Claude Code](...)` line above the
`Co-Authored-By` / `Claude-Session` trailers; the coordinator accepted that line (2026-10-17).

**Why:** on #1, the skill returned at once ("running in the background"). Committing manually at the same time would
have raced it or made a duplicate commit.

**How to apply:** after invoking it, don't touch the working tree until its task notification arrives. Then verify
with `git log -1 --format='%G? %B'` (signature `G`, `feat(#N):` prefix from the `prepare-commit-msg` hook via
`GIT_SKIP_OWNER_NAME=1`, the trailers present). Pass the hook/prefix details in the skill `args`.
