"""Tests for `GET /api/health` and the `/api`-prefixed OpenAPI document (spec §4, §8)."""

from http import HTTPStatus

import pytest
from fastapi.testclient import TestClient

from budge.api.app import app

HTTP_METHODS = frozenset({'get', 'put', 'post', 'delete', 'options', 'head', 'patch', 'trace'})
"""The keys of an OpenAPI path item that hold operations; the rest (`parameters`, `summary`, ...) don't."""

OPERATIONS = sorted(
    (method, path)
    for path, path_item in app.openapi()['paths'].items()
    for method in path_item
    if method in HTTP_METHODS
)
"""Every `(method, path)` operation in the module-level app's OpenAPI document."""

DOCSTRING_MARKERS = ('>>>', 'Args:', 'Returns:', 'Raises:', 'Yields:', 'Examples:')
"""Text that marks a Python docstring (doctests and Google-style sections), never meant for API readers."""


def test_health_returns_ok(client: TestClient) -> None:
    """`GET /api/health` returns `200 {"ok": true}`."""
    response = client.get('/api/health')

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'ok': True}


@pytest.mark.parametrize('path', ['/health', '/openapi.json', '/docs', '/docs/oauth2-redirect', '/redoc'])
def test_routes_are_only_served_under_the_api_prefix(client: TestClient, path: str) -> None:
    """Without the `/api` prefix there is no route, and FastAPI's default doc paths are disabled."""
    response = client.get(path)

    assert response.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.parametrize('path', ['/api/health/', '/api/docs/', '/api/openapi.json/', '/api/redoc/'])
def test_trailing_slash_is_not_redirected(client: TestClient, path: str) -> None:
    """A trailing slash gets a same-origin `404`, not Starlette's `307` to the slashless path.

    Starlette builds that redirect's `Location` from the `Host` header, which behind CloudFront is the API Gateway
    domain (spec §4), so following it would leave the app's origin.
    """
    response = client.get(path, follow_redirects=False)

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert 'location' not in response.headers


def test_every_api_route_is_under_the_api_prefix() -> None:
    """Every route in the module-level app's OpenAPI document lives under `/api`.

    The docs routes are left out of the document; `tests/api/test_docs.py` covers their paths.
    """
    api_paths = list(app.openapi()['paths'])

    assert api_paths
    for path in api_paths:
        assert path.startswith('/api/'), path


def test_openapi_document_describes_health(client: TestClient) -> None:
    """`/api/openapi.json` lists `/api/health` as `get_health`, with the `HealthResponse` schema."""
    response = client.get('/api/openapi.json')

    assert response.status_code == HTTPStatus.OK
    document = response.json()
    assert document['paths']['/api/health']['get']['operationId'] == 'get_health'
    health = document['paths']['/api/health']['get']['responses']['200']
    assert health['content']['application/json']['schema'] == {'$ref': '#/components/schemas/HealthResponse'}
    assert document['components']['schemas']['HealthResponse']['properties']['ok']['const'] is True


def test_operation_walk_finds_the_health_check() -> None:
    """The walk reads the document's operations, so the parametrized check below can't pass vacuously."""
    assert ('get', '/api/health') in OPERATIONS


@pytest.mark.parametrize(('method', 'path'), OPERATIONS)
def test_operation_descriptions_hold_no_docstring_markup(method: str, path: str) -> None:
    """No operation's OpenAPI `description` carries doctests or Google-style docstring sections.

    FastAPI publishes a path operation function's docstring as its `description` unless the route passes
    `description=`, so a route function's doctest would otherwise show up in Swagger UI and ReDoc.
    """
    description: str = app.openapi()['paths'][path][method].get('description', '')

    for marker in DOCSTRING_MARKERS:
        assert marker not in description, f'{method.upper()} {path}: {description!r}'


def test_health_operation_description() -> None:
    """`GET /api/health` is described for API readers only, without its function's doctest."""
    description = app.openapi()['paths']['/api/health']['get']['description']

    assert description == 'Report that the API is up. Unauthenticated, so the deploy smoke test can call it.'
