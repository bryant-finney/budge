---
name: github-stacked-prs
description: GitHub's issue-dependencies API rejects pull requests, and stacked PRs don't link Closes #N until they target main
metadata:
  type: reference
---

# GitHub: stacked PRs and dependencies

- `gh api -X POST repos/<owner>/<repo>/issues/<pr>/dependencies/blocked_by -F issue_id=<id>` fails with HTTP 422,
  "Source issue may only be an issue, Target issue may only be an issue", when either side is a PR (tried on
  budge #20 blocked by #19, 2026-10-17). Record PR-to-PR ordering as a prose `Blocked by #N (stacked on <branch>)`
  line in the PR body. Issue-to-issue links already record the dependencies.
- A PR whose base isn't the default branch shows no `closingIssuesReferences`: `Closes #N` only links (and closes)
  once the PR targets `main`. When the lower PR merges with branch deletion, GitHub retargets the stacked PR to
  `main` and the link appears; otherwise retarget by hand before merging.

**How to apply:** for stacked back-end PRs (#19 → #20 → #21 ...), skip the dependencies API call and expect
`gh pr view --json closingIssuesReferences` to be empty until the PR is retargeted.
