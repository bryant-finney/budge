---
name: mangum-event-loop
description: Mangum 0.22 needs a current asyncio loop; how the test suite owns it on 3.11-3.15 without fatal warnings
metadata:
  type: reference
---

# Mangum 0.22 and the current event loop

- `Mangum.__init__` probes `asyncio.get_event_loop()` and creates and sets a loop if there's none. On 3.12-3.13 the
  probe emits `DeprecationWarning: There is no current event loop` (pyproject ignores it, scoped to
  `mangum.adapter`). On 3.14+ the probe raises, and Mangum catches it. Each request then runs on
  `asyncio.get_event_loop()` (`HTTPCycle.__call__`). That is fine on Lambda, where the import-time loop stays
  current.
- In pytest, `asyncio.run` doctests (and any `pytest.mark.anyio` test; there are none since `61dbe8e`, and
  `TestClient` runs on its own portal thread) unset the current loop when they finish. A later handler call
  then warns or raises, and the unowned import-time loop is garbage-collected unclosed. That `ResourceWarning`
  becomes `PytestUnraisableExceptionWarning`, which lands at session end or inside a random test.
- Fix (rootdir `src/back-end/conftest.py`): import `budge.api.handler` when the conftest loads, keep
  `MANGUM_LOOP = asyncio.get_event_loop()`, re-set it in the `current_event_loop` fixture that handler tests use, and
  close it in a session-scoped autouse fixture. Don't create a fresh loop per test: that orphans Mangum's loop.
- It must be the rootdir conftest, not `tests/conftest.py`: `testpaths` is `["budge", "tests"]`, and doctest
  collection of `budge/api/handler.py` creates the loop on its own. With the fix in `tests/conftest.py`,
  `pytest budge` and `pytest budge/api` failed (exit 1, `ResourceWarning: unclosed event loop`) on 3.11-3.15 while
  the full run passed (PR #26 review). The three pieces move as a unit; the root `conftest.py` is listed in mypy
  `files`, pyright `include` and ty `src.include`, and ruff checks it with the root config (no `tests/ruff.toml`).
- The bug only showed on some versions. Run the full matrix (`UV_PYTHON=3.11 ... 3.15`) on a clean export before
  calling it green: a 3.15-only run passed while 3.13 failed. Also run `pytest budge` alone: a full-suite pass
  doesn't cover a doctest-only run.
- `handler` uses `lifespan='off'`, so the app's lifespan never runs on Lambda (it does under `TestClient` and
  uvicorn). Keep per-process setup at module scope (spec §8's JWKS cache); see `budge/api/handler.py`.

Related: [[local-python-matrix]], [[starlette-testclient-httpx2]].
