---
name: gh-pr-body-trailing-newline
description: gh pr view --jq .body appends a newline, so feeding it back through --body-file grows the PR body on each round trip
metadata:
  type: project
---

# PR body round trips add a newline

`gh pr view <n> --json body --jq .body > file` writes the body plus one newline, and
`gh pr edit <n> --body-file file` stores the file as is, so each round trip adds a trailing newline
to the PR body.

**Why:** On PR #34 (2026-11-03) a one-line edit also grew the body from 2 trailing newlines to 3, and
only a byte comparison after the edit showed it. A second write was needed to remove it.

**How to apply:** Read the body from `gh api repos/<owner>/<repo>/pulls/<n>` as JSON, change it, and
send it back with `gh api -X PATCH ... --input -`, or strip the one extra newline before uploading.
Compare the stored body with the intended text afterwards.
