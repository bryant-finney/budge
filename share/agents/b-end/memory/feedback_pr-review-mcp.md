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
