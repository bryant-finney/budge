---
name: agent-worktree-isolation
description: an isolated agent can't write to or run git in any worktree but its own, so "one worktree per PR" collapses to stacked branches in one worktree; the guard also rejects compound or variable-laden commands
metadata:
  type: project
---

# Worktree-isolated agent sessions

- **No second worktree.** `git worktree add` from the agent's worktree works. After that, `cd`
  into the new worktree for git is refused, and `EnterWorktree` with its path is refused too
  ("would not give this agent write access"). On 2026-10-27, the coordinator asked for one
  worktree per PR for #15/#16/#17/#28. I removed the empty extra worktree and built each stacked
  branch in my own worktree instead (`git checkout -b <next> <prev>`).
- **The guard rejects compound commands.** Commands that chain git or gh with other tools, loop
  over `gh`, or use `$PWD`/variables in a tool's PATH get "too complex to verify". Run one plain
  command per call. `uv run --output-format=github …` chained with others was also refused.
- **pre-commit wrapper:** use a git-ignored `.cache/bin/pc` that prepends `.cache/bin` (with the
  `pnpm` shim) to the real PATH. Replacing PATH with a short literal broke goenv's Go, so the
  gitleaks hook failed to build (`compile: version "go1.22.3" does not match go tool version`).
- **gh stack:** the `github/gh-stack` extension isn't installed. Agents must not install it, so
  stacks rely on plain `--base` chaining.

**Why:** these blocked or broke steps in the #15–#28 session.
**How to apply:** plan per-issue branches in one worktree, keep each Bash call to a single plain
command, and tell the coordinator early when a per-worktree instruction can't be met. See also
[[git-worktree-restack]] and [[ci-node-setup]].
