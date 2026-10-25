---
name: git-worktree-restack
description: restacking #21/#22-style stacked PRs whose branches live in separate worktrees; `--update-refs` can't move a branch checked out elsewhere
metadata:
  type: project
---

# Restacking PRs across worktrees

Each stacked PR has its own agent worktree (`.claude/worktrees/pr-<n>`), so each branch is checked
out somewhere. `git rebase --update-refs` skips refs checked out in another worktree, so
rebasing from the top branch with `--update-refs` leaves the lower branch behind.

**Why:** an infra handoff note of 2026-10-18 recommended `--update-refs`; on 2026-10-20 the user
restacked #21/#22 onto `main` by hand because #21 lives in `pr-21` and #22 in `pr-22`.

**How to apply:**

1. In the lower worktree: note its tip, then `git rebase origin/main`.
2. In the upper worktree: `git rebase --onto <lower branch> <old lower tip> <upper branch>`.
3. `git range-diff` must show every patch as `=`; then push bottom-up with
   `git push --force-with-lease=<branch>:<old sha> origin <branch>`.
4. Afterwards each branch's ahead count must be unchanged, and every behind count 0
   (`git rev-list --left-right --count origin/main...<branch>`).
5. A rebase strands the SHAs that issues and PR threads cite. Map them with
   `git patch-id --stable` and post the map on the PR.

Related: [[git-commit-hook-gotchas]].
