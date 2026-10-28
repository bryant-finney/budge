---
name: pr-feedback-loop
description: Use when asked to start or resume recurring monitoring of Budge pull request comments and reviews, including agent follow-up in PR worktrees and optional merging of approved PRs.
---

# PR feedback loop

Monitor open PRs in `bryant-finney/budge` hourly by default. Use this workflow from Codex,
Claude Code, or another agent host; adapt tool names to the host's actual capabilities.

## Start or resume

1. Read the repository instructions and recover any existing loop's checkpoint. Reuse the loop
   rather than starting a second scheduler or a second worker for the same PR.
2. Record the interval, repository, next poll time, and authorized actions. A request to handle
   feedback permits scoped fixes, signed commits, pushes, and feedback replies. Merge only when
   the user requested it; retain authorization across polls without asking again. A skill alone
   grants no permission to mutate GitHub or bypass host approvals.
3. Use an available recurring scheduler and verify the saved task. Otherwise, run an immediate
   scan and use interruptible waits in the current session. Report the actual mode and next poll
   time: an in-session wait is not a saved schedule and ends when the session ends. If neither is
   available, report that limitation instead of claiming monitoring started.

## Each poll

Fetch all open PRs, including drafts, with paginated discussion comments, submitted reviews,
inline review threads and replies, head SHA, base branch, labels, and checks. See
[GitHub operations](references/github.md) for API details. Process outstanding actionable
feedback on the first scan, even when it predates startup.

Maintain a checkpoint in host state or an untracked local state file: per-PR comment IDs and
edit timestamps, review IDs and states, thread resolution, head SHA, pending feedback, active
worker, and last successful scan. Detect edits as well as additions. Mark work handled only
after verified completion; retain pending work for retry. A failed or incomplete fetch does
not advance that PR's checkpoint or establish merge eligibility.

Report each PR with new comment or review activity, its URL, and the action taken. Keep idle
polls brief. Re-evaluate pending work and merge candidates even without new comments.

## Route feedback

| Scope                                                             | Agent   |
| ----------------------------------------------------------------- | ------- |
| Back-end Python, dependencies, tests, Dockerfile, Python hooks    | `b-end` |
| Front-end TypeScript, Svelte, UX, front-end hooks                 | `f-end` |
| Infrastructure, workflows, root tooling, repository configuration | `infra` |

Use labels, changed files, and the feedback's subject together. Match the current PR head
branch to `git worktree list --porcelain`; reuse that worktree, or add one under
`.claude/worktrees/` if none exists. Verify its branch, working tree, and remote tip before
editing. Preserve existing edits and coordinate cross-layer ownership.

The loop runs in the root clone on `main`, and a worker inherits that directory. Do all PR work
in the PR's worktree:

- Pass the worker the worktree's absolute path. It changes into that directory first, uses
  absolute paths under it for reads and edits, and never edits, stages, or commits in the root
  clone. Don't use the host's own worktree isolation (it creates a new, unrelated worktree).
- Agent memory belongs in the worktree's `share/agents/<role>/memory/`, committed with the PR.
  `.claude/agent-memory/` in the root clone links to the root clone's copy.
- Run the commit skill, and anything else that writes, from the worktree. A skill that forks or
  starts from the session's directory lands in the root clone; commit directly instead.
- Snapshot `git status` in the root clone before delegating, and compare it afterwards. Report
  and undo any change the worker made there.

Delegate through the host's agent facility, giving the worktree path, explicit file ownership,
feedback URLs, thread IDs, and the instruction that other agents' edits must be preserved. If
delegation is unavailable, follow the matching role under `share/agents/` yourself and disclose
the fallback.
Require relevant checks, `pre-commit`, the repository commit skill, signed commits, verified
pushes, and evidence-backed replies. Resolve threads only after addressing them. Track ordinary
discussion requests too; they have no GitHub thread-resolution flag. Keep one worker per PR.

## Merge and continue

When merging is authorized, refresh approval state, outstanding feedback, checks, draft status,
mergeability, base branch, and exact head SHA immediately before each merge. Read submitted
reviews even when summary fields are empty. A later change request or dismissal supersedes
that reviewer's earlier approval; respect the live approval requirements after pushes.

Merge only approved PRs with every actionable request addressed, every review thread resolved,
and applicable checks passing. Wait for pending checks; report failures or missing required
checks. Merge stack parents and declared prerequisite PRs first, even when the candidate
already targets `main`. Use merge commits and a head-SHA guard. Never enable a
rule bypass, change protections, or push directly to `main` to make a merge succeed. Verify
the final merged state, then refresh dependent PRs before evaluating them.

Resume the hourly cadence after worker completion and merge attempts. Stop on the user's
request or when no open PRs remain; report blockers and any work still running.
