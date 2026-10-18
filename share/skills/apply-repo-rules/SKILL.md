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

A pre-approval covers a command string, not the code it runs, so the script limits what it
trusts:

- The target repo is fixed (`bryant-finney/budge` on `github.com`), not read from git remotes or
  `gh`'s config.
- Without a ref, it asks the API where `main` is and fetches it from
  `https://github.com/bryant-finney/budge.git`, not from `origin`. It never falls back to a cached
  copy.
- It reads `rules.md` and `parse-rules.jq` from the same commit, never from the working tree.
- `apply` refuses to run unless this directory on disk matches that `main` commit, so only code
  that merged with `rules.md` can write. This stops accidents, such as running `apply` while
  editing the parser. An edited copy of the script can drop the check, so it doesn't stop a
  misbehaving agent.

## Commands

Run from the repository root, exactly as written. The `allowed-tools` patterns match the literal
command, so a `cd`, an env-var prefix, `bash <path>`, or an absolute path won't match them and
needs approval again.

| Command                                                             | Effect                                                                                                                                | Approval                                     |
| ------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------- |
| `share/skills/apply-repo-rules/apply-repo-rules.sh check`           | Read-only. Compares the live settings with `rules.md` on `main`: `OK`/`FAIL` per ruleset and for repo settings, with a diff.          | None (pre-approved)                          |
| `share/skills/apply-repo-rules/apply-repo-rules.sh check <ref>`     | The same, against `rules.md` at `<ref>`, such as `HEAD` on a PR branch.                                                               | None (pre-approved)                          |
| `share/skills/apply-repo-rules/apply-repo-rules.sh apply`           | Converges GitHub to `rules.md` on `main`, then runs `check`. Creates and updates; never deletes.                                      | None: merging is the approval (pre-approved) |
| `share/skills/apply-repo-rules/apply-repo-rules.sh apply-ref <ref>` | The same as `apply`, from `<ref>`. It skips the check that this directory matches `main`, so the user's approval covers the code too. | The user's, every time (not pre-approved)    |

| Exit | Meaning                                                                                    | What to do                                              |
| ---- | ------------------------------------------------------------------------------------------ | ------------------------------------------------------- |
| 0    | No drift.                                                                                  | Report the output.                                      |
| 1    | Drift (`FAIL` lines).                                                                      | Report the diff. After a merge, run `apply`.            |
| 2    | The ref, `rules.md`, or `parse-rules.jq` is missing at the ref, or `rules.md` won't parse. | Fix the ref or the tables. Don't retry as is.           |
| 3    | `main` can't be fetched from GitHub.                                                       | Retry once, then report. Never use a cached `main`.     |
| 4    | `apply` refused: this directory differs from the `main` commit it would apply.             | Run it from a checkout of current `main`, or report it. |
| 5    | A GitHub API call failed, or two rulesets share a name.                                    | Report the error. Live state is unknown.                |
| 64   | Usage error.                                                                               | Run the command exactly as written above.               |

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
| Treating a `NOTE ... not in rules.md, so not compared` as drift | It isn't. `check` compares only the rule parameters `rules.md` sets. To pin one of them, add it to `rules.md` in a PR.                   |
| Editing the skill and running `apply` to test it                | `apply` refuses (exit 4) and runs only merged code. Preview with `check HEAD`, and let the user merge before `apply`.                    |
| `FAIL rulesets not in rules.md`                                 | Report it. Removing a ruleset is the user's call (the spec's Roll back procedure), so the script never deletes.                          |
| `check` shows `enforcement` `disabled`                          | The user may be partway through the spec's emergency path. Ask before running `apply`, which turns enforcement back on.                  |
