# b-end TODO

Progress handoff for a cold-started b-end agent. Snapshot taken 2026-10-18 after `git fetch origin`. Re-check
every SHA before acting (`git fetch origin && git log --oneline origin/main..origin/<branch>`).

## Stack state

PR #19 (issue #1) is merged: `main` is at `11bcb76`.

| PR  | Issue | Branch                    | Base                      | Head                                   |
| --- | ----- | ------------------------- | ------------------------- | -------------------------------------- |
| #20 | #2    | `feat/2/static-analysis`  | `main`                    | `e1524fe`                              |
| #23 | #3    | `feat/3/domain-protocols` | `feat/2/static-analysis`  | `111c4de`                              |
| #26 | #4    | `feat/4/fastapi-health`   | `feat/3/domain-protocols` | the commit that last updated this file |

- The stack is current: each branch is 0 behind its base. Worktrees: `.claude/worktrees/pr-20`, `pr-23`, `pr-26`.
- To propagate a change in a lower PR, rebase each worktree onto the local branch below it (`git rebase feat/2/static-analysis` in `pr-23`, then `git rebase feat/3/domain-protocols` in `pr-26`). `--update-refs` can't move
  a branch that another worktree has checked out. Push with `--force-with-lease=<branch>:<old sha>`.
- `share/agents/b-end/memory/MEMORY.md` gets index lines from every branch. On a conflict, keep the union of the
  lines, without duplicates.
- Checks after a restack: run the gate on a `git archive` export of each tip, never in a shared worktree. Run pytest
  on 3.11-3.15 (see `memory/mangum-event-loop.md`).

## Review state (2026-10-18 pass)

Every earlier review thread on #20 and #23 is addressed and has a reply naming the commit. Threads stay open for the
user to resolve.

- **#20:** the earlier threads are addressed in `8b90474` (mypy `ignore-without-code`; pyright
  `enableTypeIgnoreComments = false` and `reportUnnecessaryTypeIgnoreComment`) and `e1524fe` (ruff `PGH003`/`PGH004`,
  a separate commit because it deviates from #2's exact `select`). The new review suggests extra mypy error codes,
  `pythonPlatform`/`platform = linux`, and `docstring-code-format`.
- **#23:** the earlier threads are addressed in `c9f72e7` (`ExcludedReason` in the leaf `budge.models`), `b633ee6`
  (`FiniteFloat` and the `currency` note), `0763f2e` (order-free asserts) and `111c4de`
  (`trigger(connection_id: str | None)`, a separate commit). The new review covers lax vs. `strict=True`,
  `put_transaction_rows` row ownership, and a docstring nit.
- **#26:** first maintainer-facing review posted. Main finding: the run-summary log line can't be read by §12's
  metric filter as currently logged. Once the user approved it, `61dbe8e` swapped the `httpx` dev dependency for
  `httpx2` and moved the API tests to FastAPI's `TestClient`.

## Blocked or pending the user

- **Judgment calls the user may revert:** #20's `PGH003`/`PGH004` (`e1524fe`) and #23's `trigger()` shape (`111c4de`).
- **Spec gap:** Plaid's nullable `iso_currency_code` versus §6's non-null `currency`. M2's normalization must pick.
- **`Closes #N` only takes effect once that PR's base is `main`**; see `memory/github-stacked-prs.md`.

## Next in the back-end queue

- **#5:** add `repo: local` ruff, ruff-format, mypy and pyright hooks run through `uv` to the root
  `.pre-commit-config.yaml`. Depends on #1 and #2.
- **#11:** backend Dockerfile skeleton (Lambda `python:3.14`, linux/arm64, uv-locked deps). Depends on #1 and #4.
  `budge.__version__` falls back to `0.0.0` without an installed dist-info (#19), so a copy-only image works.
  Installing the project still gives the real version.
- After that, M2 (milestone 2) work starts: the auth dependency, the error envelope, the §8 routes, `run_ingestion`,
  `classify`, and the `budge.aws` adapters.
