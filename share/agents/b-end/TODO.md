# b-end TODO

Progress handoff for a cold-started b-end agent. Snapshot taken 2026-10-17 after `git fetch origin`. Re-check
every SHA before acting (`git fetch origin && git log --oneline origin/main..origin/<branch>`).

## Stack state

| PR  | Issue | Branch                      | Base                        | Head      | vs. base              |
| --- | ----- | --------------------------- | --------------------------- | --------- | --------------------- |
| #19 | #1    | `feat/1/back-end-bootstrap` | `main` (`8ba6f0e`)          | `3ce8eee` | 3 ahead, 4 behind     |
| #20 | #2    | `feat/2/static-analysis`    | `feat/1/back-end-bootstrap` | `eb15b6c` | 1 ahead, **2 behind** |
| #23 | #3    | `feat/3/domain-protocols`   | `feat/2/static-analysis`    | `7472d5f` | 1 ahead, 0 behind     |
| #26 | #4    | `feat/4/fastapi-health`     | `feat/3/domain-protocols`   | `4f0c4e1` | 2 ahead, 0 behind     |

- **Restack needed.** `feat/1` gained `0d429d7` (version from git tags via hatchling + uv-dynamic-versioning) and
  `3ce8eee` (memory notes), so #20, #23 and #26 are stale. `main` is at `8ba6f0e` (#25 merged), 4 commits past
  `feat/1`'s base. The user decides whether `feat/1` goes onto `main` first.
  - Restack from the `feat/4` tip in one pass: `git rebase --update-refs --onto origin/feat/1/back-end-bootstrap 6f9da34 feat/4/fastapi-health`. `6f9da34` is the old `feat/1` tip, so only #2-#4's commits are replayed.
    Then push each branch bottom-up with `--force-with-lease=<branch>:<old sha>`.
  - Verify afterwards: #20 and #23 are exactly 1 ahead of their new bases, #26 is 2 ahead (`4f0c4e1` plus the
    commit adding this file, which can't list its own SHA), and each is 0 behind.
- **Expected conflicts:**
  - `src/back-end/pyproject.toml` when replaying #20: `feat/1` replaced `uv_build` with hatchling and made
    `version` dynamic, and #20 adds the ruff/mypy/pyright config and dev deps. Merge by hand.
  - `src/back-end/uv.lock`: don't hand-merge it. Take `feat/1`'s, then run `uv lock` and commit the result.
  - #26's `filterwarnings` edit sits near `addopts`. Check it still applies.
  - `share/agents/b-end/memory/MEMORY.md`: `main`, `feat/1`, #20, #23 and #26 each append different index lines
    after the header. Resolve every time by keeping the union of the lines, without duplicates.
- **Checks after a restack:** run the gate on a `git archive` export of each tip, never in a shared worktree. Run
  pytest on 3.11-3.15, as described in `memory/mangum-event-loop.md`.

## Open review findings

### #19 (`feat/1`): [review](https://github.com/bryant-finney/budge/pull/19#pullrequestreview-5560885705)

- [ ] **Medium:** `src/back-end/budge/__init__.py:22`.
  - `__version__ = importlib.metadata.version(__name__)` raises `PackageNotFoundError` when #11's Dockerfile copies
    `budge/` into `LAMBDA_TASK_ROOT` without installing the project's dist-info.
  - **Still open at `3ce8eee`.** uv-dynamic-versioning's `fallback-version = "0.0.0"` applies at build time only, so
    it doesn't change the import-time lookup. It does make it possible to build without `.git`, which enables the
    preferred fix.
  - Preferred fix (in #11): install the project itself, `uv pip install --no-deps --target "${LAMBDA_TASK_ROOT}" .`,
    instead of a raw `COPY budge/`, and update the #11 issue body to match.
  - Alternative: catch `PackageNotFoundError` in `budge/__init__.py` and test that branch.
- [ ] **Nit, no change needed:** `--cov` is in `addopts` (`pyproject.toml:45` at `3ce8eee`), so a single-file run
  fails `fail_under`. Use `--no-cov` when iterating.

### #20 (`feat/2`): [review](https://github.com/bryant-finney/budge/pull/20#pullrequestreview-5560884658)

Line numbers are for `src/back-end/pyproject.toml` at `eb15b6c`. They shift after the restack.

- [ ] **pyright, `:59`:** add `enableTypeIgnoreComments = false` and `reportUnnecessaryTypeIgnoreComment = "error"`.
  Pyright currently reads mypy's `# type: ignore[...]` as a blanket ignore and never reports stale ones.
- [ ] **mypy, `:48`:** add `enable_error_code = ["ignore-without-code"]` so a bare `# type: ignore` fails.
- [ ] **ruff, `:89`:** `PGH004` and `PGH003` (blanket `noqa` and blanket `type: ignore`). These deviate from #2's
  exact `select` list, so **they need the maintainer's call before you add them.**

### #23 (`feat/3`): [review](https://github.com/bryant-finney/budge/pull/23#pullrequestreview-5560886508)

Line numbers are for `src/back-end/` at `7472d5f`. All five findings are still open.

- [ ] **Medium:** `budge/ingestion/trigger.py:17` (and the stub at `budge/aws/ingestion.py:28` and the fake at
  `tests/fakes.py:124`). `Sequence[str] | None` accepts a bare `str`.
  - Either collapse the parameter to `connection_id: str | None` or narrow it to
    `list[str] | tuple[str, ...] | None`. The reviewer leaves the choice to the maintainer.
  - Add a test that a bare string is rejected.
- [ ] **Low-medium:** `budge/models.py:16` imports `budge.classify`, which becomes a cycle once M2's
  `classify(txn: Transaction)` imports `budge.models`. Move `ExcludedReason`, `COUNT` and `NO_PFC_CATEGORY` into a
  leaf module (`budge/models.py` or a new `budge/vocabulary.py`) and re-export them from `budge.classify`.
- [ ] **Low:** `budge/models.py:141`, `amount: float`, accepts NaN and inf. NaN serializes to `null` and then fails
  to read back. Use `pydantic.FiniteFloat`, and add `('amount', float('nan'))` to
  `test_transaction_rejects_invalid_values`.
- [ ] **Low, spec gap:** `budge/models.py:144`, `currency: str`. Plaid's `iso_currency_code` is nullable, which is
  only a concern when `unofficial_currency_code` is set. Note it in the docstring or §6 so that M2's normalization
  decides deliberately.
- [ ] **Nit:** `tests/test_protocols.py:73-74`. The `get_transactions` assertions depend on order, but the protocol
  promises no order. Compare `sorted(..., key=lambda t: t.transaction_id)`.

### #26 (`feat/4`)

- [x] Copilot's [overview review](https://github.com/bryant-finney/budge/pull/26#pullrequestreview-5560950034)
  found no issues.
- [ ] The maintainer hasn't reviewed it yet.
- #26 depends on none of #23's weak spots, so fixing them shouldn't touch #26.

## Blocked or pending the user

- **The `httpx` to `httpx2` dev-dependency swap was denied by the permission classifier** (`uv add --group dev 'httpx2~=2.13'`). Starlette 1.8's `TestClient` wants `httpx2`, so #26's tests use `httpx.ASGITransport` instead.
  Once the user approves the swap, `TestClient` can come back. See `memory/starlette-testclient-httpx2.md`.
- **`Closes #4` in #26, `Closes #3` in #23, and so on only take effect once that PR's base is `main`.** GitHub
  doesn't link closing keywords on stacked bases; see `memory/github-stacked-prs.md`.
- The maintainer decides #20's PGH rules and #23's `trigger()` signature (see above).

## Next in the back-end queue

- **#5:** add `repo: local` ruff, ruff-format, mypy and pyright hooks run through `uv` to the root
  `.pre-commit-config.yaml`. Depends on #1 and #2.
- **#11:** backend Dockerfile skeleton (Lambda `python:3.14`, linux/arm64, uv-locked deps). Depends on #1 and #4.
  Settle #19's `__version__` / dist-info finding here: install the project, don't `COPY budge/`.
- After that, M2 (milestone 2) work starts: the auth dependency, the error envelope, the §8 routes, `run_ingestion`,
  `classify`, and the `budge.aws` adapters.
