"""Shared pytest fixtures: the API test clients, recorded Lambda events, and a Lambda context double.

The API clients get their auth dependencies from `tests.auth.configure`: test settings, a fake secret store and a
self-signed Google key set, so nothing reads the environment or the network.

Mangum's import-time event loop (`MANGUM_LOOP`, the `current_event_loop` fixture) is set up in the rootdir
`conftest.py`, so `pytest budge` doctest-only runs get it too.
"""

import dataclasses
import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from mangum.types import LambdaCognitoIdentity, LambdaContext, LambdaMobileClientContext

from budge.api.app import create_app
from budge.api.auth import require_session
from tests.auth import OTHER_SUB, client_for, configure, session_token
from tests.fakes import deny_session

EVENTS_DIR = Path(__file__).parent / 'events'
"""Recorded (or docs-derived) Lambda event payloads."""


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
    """FastAPI's in-process `TestClient` for a fresh app, signed in as an allowlisted user (`tests.auth.ALLOWED_SUB`).

    It is entered, so the app's lifespan runs as on uvicorn. The lifespan never runs on Lambda: `budge.api.handler`
    wraps the app with `lifespan='off'`. Keep per-process setup (signing keys, the JWKS cache) at module scope, as spec
    §8 caches the JWKS "at Lambda module scope", not in a lifespan hook: a route that relied on one would pass here and
    under uvicorn but fail once deployed.

    It needs the `httpx2` dev dependency: Starlette 1.8's test client is built on `httpx2` and warns (fatal under
    `filterwarnings = error`) if only `httpx` is installed.
    """
    with client_for(configure(create_app()), token=session_token()) as test_client:
        yield test_client


@pytest.fixture
def anonymous_client() -> Iterator[TestClient]:
    """A client for a fresh, test-configured app, with no session cookie."""
    with client_for(configure(create_app())) as test_client:
        yield test_client


@pytest.fixture
def outsider_client() -> Iterator[TestClient]:
    """A client for a fresh, test-configured app, with a valid session for a `sub` that isn't allowlisted."""
    with client_for(configure(create_app()), token=session_token(OTHER_SUB)) as test_client:
        yield test_client


@pytest.fixture
def denied_client() -> Iterator[TestClient]:
    """A client for a fresh app whose `require_session` rejects every request with `deny_session`'s `401`.

    The override is set on that app alone, so the module-level `app` and other `create_app()` apps stay open.
    """
    application = create_app()
    application.dependency_overrides[require_session] = deny_session
    with TestClient(application) as test_client:
        yield test_client


@pytest.fixture
def lambda_context() -> LambdaContext:
    """A Lambda context object."""
    return FakeLambdaContext()


@pytest.fixture
def apigw_v2_get_health() -> dict[str, object]:
    """An API Gateway HTTP API (payload format 2.0) event for `GET /api/health` arriving through CloudFront.

    It matches the `/api/*` behavior's `AllViewerExceptHostHeader` origin request policy (spec §4): the viewer's
    headers (a `curl` smoke test's User-Agent) plus CloudFront's `cloudfront-*` headers, and `sourceIp` is the
    CloudFront edge, the last `x-forwarded-for` hop. The viewer's own address is only in `cloudfront-viewer-address`.
    """
    return load_event('apigw-v2-get-health')
