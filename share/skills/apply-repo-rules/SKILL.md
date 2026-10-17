---
name: apply-repo-rules
description: Use when checking or applying budge's GitHub branch and tag rulesets or repo merge settings, verifying they match the repo protection spec, or after a change to rules.md merges to main.
allowed-tools: Bash(share/skills/apply-repo-rules/apply-repo-rules.sh check) Bash(share/skills/apply-repo-rules/apply-repo-rules.sh check *) Bash(share/skills/apply-repo-rules/apply-repo-rules.sh apply)
---

# Apply repo rules

## Overview

[`rules.md`](rules.md) defines the desired rulesets and merge settings as tables, and
[`share/agents/infra/repo-protection.md`](../../agents/infra/repo-protection.md) explains them.
[`apply-repo-rules.sh`](apply-repo-rules.sh) is the only interface agents use to read or change
these GitHub settings. In Claude Code, this skill's `allowed-tools` frontmatter pre-approves
`check` and `apply` while the skill is active. `apply-ref` is left out on purpose, so it always
needs the user's approval. Other hosts ignore `allowed-tools`, so their users approve each
command by hand.

## Commands

Run from the repository root, exactly as written. The `allowed-tools` patterns match the literal
command, so a `cd`, an env-var prefix, `bash <path>`, or an absolute path won't match them and
needs approval again.

| Command                                                             | Effect                                                                                                                              | Approval                                     |
| ------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------- |
| `share/skills/apply-repo-rules/apply-repo-rules.sh check`           | Read-only. Compares the live settings with `rules.md` on `origin/main`: `OK`/`FAIL` per ruleset and for repo settings, with a diff. | None (pre-approved)                          |
| `share/skills/apply-repo-rules/apply-repo-rules.sh check <ref>`     | The same, against `rules.md` at `<ref>`, such as `HEAD` on a PR branch.                                                             | None (pre-approved)                          |
| `share/skills/apply-repo-rules/apply-repo-rules.sh apply`           | Converges GitHub to `rules.md` on `origin/main`, then runs `check`. Creates and updates; never deletes.                             | None: merging is the approval (pre-approved) |
| `share/skills/apply-repo-rules/apply-repo-rules.sh apply-ref <ref>` | The same as `apply`, from any other ref.                                                                                            | The user's, every time (not pre-approved)    |

`check` exits 1 on drift. Every command exits 2 when `rules.md` doesn't exist at the ref.

## Changing a rule

1. Edit the tables in `rules.md` and the rationale in the spec, in one PR. Run `check HEAD` to
   preview the diff against the live settings.
2. After the user merges the PR, run `apply`.
3. Report the `check` output verbatim.

## Common mistakes

| Mistake                                                         | Fix                                                                                                                                      |
| --------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| Calling `gh api` on rulesets or repo settings directly          | Use the script. Its `allowed-tools` pre-approve only the script's `check` and `apply`, run exactly as written.                           |
| Running `apply-ref` without the user's approval in this session | Ask first, naming the ref. `apply-ref` is never pre-approved. If the host denies it, report it and stop. Don't retry it in another form. |
| `FAIL` only because a live rule has new defaulted parameters    | Add the parameters to `rules.md` in a PR. That isn't drift, and `apply` can't remove server defaults.                                    |
| `FAIL rulesets not in rules.md`                                 | Report it. Removing a ruleset is the user's call (the spec's Roll back procedure), so the script never deletes.                          |
| `check` shows `enforcement` `disabled`                          | The user may be partway through the spec's emergency path. Ask before running `apply`, which turns enforcement back on.                  |
