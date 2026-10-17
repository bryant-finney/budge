---
name: github-settings-apply-blocked
description: Claude Code auto mode blocks gh api mutations of rulesets and repo settings (and later even read-only GETs in that context) even after user approval relayed by the coordinator
metadata:
  type: project
---

# GitHub settings apply is blocked in auto mode

On 2026-10-17 the auto-mode classifier denied every attempt to apply the
[repo-protection spec](../repo-protection.md), even after the user approved it through the
coordinator. The denied calls were `gh api --method POST .../rulesets`,
`gh api -X PATCH repos/bryant-finney/budge`, and the spec's read-only drift check. The mutations were refused as
"Account & Standing-Rule Changes". Once that refusal was in context, plain `GET`s of rulesets and
repo settings were refused too.

**Why:** the classifier treats GitHub ruleset and repo-setting changes as standing-rule changes,
and approval relayed by another agent isn't the user's own consent.

**How to apply:** don't plan on an agent running the apply. Stage the payloads, hand the user the
exact commands from the spec's Procedures section, and stop at the first denial without working
around it. If the user wants agents to apply settings, they have to add a Bash permission rule
themselves.
