---
name: pr-review-mcp
description: gh MCP pull_request_review_write quirks when posting PR reviews (commitID must be a full SHA; owner PRs only accept COMMENT)
metadata:
  type: feedback
---

# gh MCP PR review quirks

When posting a review with the gh MCP `pull_request_review_write` method `create`, leave out `commitID`, or pass the full 40-char SHA. A short SHA fails with "Could not coerce value ... to GitObjectID".

**Why:** this happened while reviewing PR #19 (2026-10-17). Leaving `commitID` out reviews the PR head, which is what you want.

**How to apply:** PRs in budge are authored by the owner's own account, so submit with event `COMMENT`; approve and request-changes are rejected. Before adding inline comments, count the line numbers against the file at the PR head, and check existing reviews (Copilot) so you don't duplicate them. See also [[stack-rebase-checks]].

**Plain `gh api` works as well (used 2026-10-18):** write `{"commit_id": <full sha>, "event": "COMMENT", "body", "comments": [{"path", "line", "side": "RIGHT", "body"}]}` to a scratch JSON file and post it with `gh api repos/<o>/<r>/pulls/<n>/reviews --input <file>`, which submits the whole review in one call. Reply on a thread with `gh api repos/<o>/<r>/pulls/<n>/comments/<id>/replies -F body=@<file>`. Bodies in files avoid zsh quoting bugs with backticks and apostrophes. Inline lines must fall inside the PR's diff hunks (context lines count); put anything else in the review body.
