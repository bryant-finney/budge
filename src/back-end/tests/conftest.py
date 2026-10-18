"""Shared pytest fixtures: the API test client, recorded Lambda events, and a Lambda context double."""

import asyncio
import dataclasses
import importlib
import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from mangum.types import LambdaCognitoIdentity, LambdaContext, LambdaMobileClientContext

from budge.api.app import create_app

EVENTS_DIR = Path(__file__).parent / 'events'
"""Recorded (or docs-derived) Lambda event payloads."""

# constructing the module-level `Mangum` handler creates an event loop and makes it current, exactly as at import on
# Lambda; nothing owns that loop, so hold it here: otherwise it is garbage-collected unclosed (a fatal ResourceWarning)
# once an `asyncio.run` doctest unsets the current loop. Collection doesn't run anything, so the loop is
# still current while this module is imported.
importlib.import_module('budge.api.handler')
MANGUM_LOOP = asyncio.get_event_loop()
"""The event loop Mangum created when `budge.api.handler` was imported."""


def load_event(name: str) -> dict[str, object]:
    """Load the JSON event `tests/events/<name>.json`."""
    event: dict[str, object] = json.loads((EVENTS_DIR / f'{name}.json').read_text(encoding='utf-8'))
    return event


@dataclasses.dataclass
class FakeLambdaContext:
    """Satisfies Mangum's `LambdaContext` protocol (the attributes AWS's Python runtime provides)."""

    function_name: str = 'budge-api'
    function_version: str = '$LATEST'
    invoked_function_arn: str = 'arn:aws:lambda:us-east-1:123456789012:function:budge-api'
    memory_limit_in_mb: int = 512
    aws_request_id: str = '3f7c1b4e-0000-4000-8000-000000000001'
    log_group_name: str = '/aws/lambda/budge-api'
    log_stream_name: str = '2026/10/17/[$LATEST]0123456789abcdef'
    identity: LambdaCognitoIdentity | None = None
    client_context: LambdaMobileClientContext | None = None

    def get_remaining_time_in_millis(self) -> int:
        """Pretend most of a 30-second timeout remains."""
        return 29_000


@pytest.fixture
def client() -> Iterator[TestClient]:
    """FastAPI's in-process `TestClient` for a fresh app (spec §12), entered so the app's lifespan runs as on uvicorn.

    It needs the `httpx2` dev dependency: Starlette 1.8's test client is built on `httpx2` and warns (fatal under
    `filterwarnings = error`) if only `httpx` is installed.
    """
    with TestClient(create_app()) as test_client:
        yield test_client


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


@pytest.fixture
def lambda_context() -> LambdaContext:
    """A Lambda context object."""
    return FakeLambdaContext()


@pytest.fixture
def apigw_v2_get_health() -> dict[str, object]:
    """An API Gateway HTTP API (payload format 2.0) event for `GET /api/health` arriving through CloudFront."""
    return load_event('apigw-v2-get-health')
