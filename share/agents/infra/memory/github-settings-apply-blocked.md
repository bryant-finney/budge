---
name: github-settings-apply-blocked
description: Claude Code auto mode blocks hand-written gh api calls on rulesets and repo settings (and later even read-only GETs); use the apply-repo-rules skill instead
metadata:
  type: project
---

# GitHub settings apply is blocked in auto mode

On 2026-10-17 the auto-mode classifier denied every attempt to apply the
[repo-protection spec](../repo-protection.md), even after the user approved it through the
coordinator. The denied calls were `gh api --method POST .../rulesets`,
`gh api -X PATCH repos/bryant-finney/budge`, and the spec's read-only drift check. The mutations were refused as
"Account & Standing-Rule Changes". Once that refusal was in context, plain `GET`s of rulesets and
repo settings were refused too. Writing the skill that replaced those calls was also denied once
as "Auto-Mode Bypass", until the user directed the work in the session. Without the skill's Host
setup rules in place, `apply-repo-rules.sh apply-ref <ref>` was denied the same way (2026-10-17),
even with the user's approval relayed. After that, the read-only `gh pr list`/`gh pr view`
mergeability check was denied too.

**Why:** the classifier treats GitHub ruleset and repo-setting changes as standing-rule changes,
and approval relayed by another agent isn't the user's own consent. Allow rules that the user
adds are resolved before the classifier runs, and narrow rules stay in effect in auto mode.

**How to apply:** use the [`apply-repo-rules`](../../../skills/apply-repo-rules/SKILL.md) skill
(`check`, `apply`, `apply-ref <ref>`). Never hand-write `gh api` calls against these settings.
The user owns the allow and ask rules in the skill's Host setup section. If they're missing or a
command is denied, report it and stop. Don't add the rules yourself or retry in another form.
