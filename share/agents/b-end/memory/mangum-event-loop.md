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
- Fix (`tests/conftest.py`): import `budge.api.handler` during collection, keep `MANGUM_LOOP = asyncio.get_event_loop()`, re-set it in the `current_event_loop` fixture that handler tests use, and close it in a
  session-scoped autouse fixture. Don't create a fresh loop per test: that orphans Mangum's loop.
- The bug only showed on some versions. Run the full matrix (`UV_PYTHON=3.11 ... 3.15`) on a clean export before
  calling it green: a 3.15-only run passed while 3.13 failed.

Related: [[local-python-matrix]], [[starlette-testclient-httpx2]].
