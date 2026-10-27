"""Session-wide pytest setup for both testpaths (`budge` doctests and `tests/`): Mangum's import-time event loop.

This lives at the rootdir rather than in `tests/conftest.py` because collecting `budge/api/handler.py` as a doctest
module creates Mangum's loop too. A run that collects only `budge` (`pytest budge`, `pytest budge/api`) would otherwise
leave that loop unowned and unclosed (a fatal `ResourceWarning`).
"""

import asyncio
import importlib
from collections.abc import Iterator

import pytest

# constructing the module-level `Mangum` handler creates an event loop and makes it current, exactly as at import on
# Lambda; nothing owns that loop, so hold it here: otherwise it is garbage-collected unclosed (a fatal ResourceWarning)
# once an `asyncio.run` doctest unsets the current loop. pytest imports this conftest before it collects anything, so
# the loop is still current here.
importlib.import_module('budge.api.handler')
MANGUM_LOOP = asyncio.get_event_loop()
"""The event loop Mangum created when `budge.api.handler` was imported."""


@pytest.fixture(scope='session', autouse=True)
def _close_mangum_loop() -> Iterator[None]:
    """Close Mangum's import-time event loop when the session ends."""
    yield
    MANGUM_LOOP.close()


@pytest.fixture
def current_event_loop() -> asyncio.AbstractEventLoop:
    """Make Mangum's loop the thread's current loop again, as it stays on Lambda, before a Mangum call.

    Mangum runs each request on `asyncio.get_event_loop()`, which warns (3.12-3.13) or raises (3.14+) when there is no
    current loop, and the `asyncio.run` doctests unset it when they finish.
    """
    asyncio.set_event_loop(MANGUM_LOOP)
    return MANGUM_LOOP
