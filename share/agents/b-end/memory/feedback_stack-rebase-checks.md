---
name: stack-rebase-checks
description: How to verify a rebased back-end PR stack without disturbing a dirty worktree; zsh word-splitting trap in check loops
metadata:
  type: feedback
---

# Checking a rebased PR stack

When re-running back-end checks on several branch tips, export each tip with
`git archive <branch> | tar -x -C <scratch>/<n>` and run `uv sync --all-groups` + checks there. That
keeps another agent's uncommitted WIP out of the results and never touches the shared worktree.

The Bash tool's shell is zsh: `for t in "ruff check ." ...; do uv run $t; done` does NOT word-split
`$t`, so you get "Failed to spawn: ruff check ." errors that look like the tool is missing. Spell the
commands out one at a time (or use `${=t}`).

**Why:** on 2026-10-17 the first check pass on the rebased #19/#20/#23 stack falsely reported that ruff
and mypy were missing because of this.

**How to apply:** any multi-branch verification. Note that feat/1 has pytest only; ruff, mypy, and
ty arrive with feat/2 (#20), whose tip dropped pyright; pyright returns with feat/3 (#23). Also check
`git ls-remote` before trusting a caller's claim that a branch is "pushed" (feat/4 was not).
