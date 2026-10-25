"""Tests for `GET /api/health` and the `/api`-prefixed OpenAPI document (spec §4, §8)."""

from http import HTTPStatus

import pytest
from fastapi.testclient import TestClient

from budge.api.app import app


def test_health_returns_ok(client: TestClient) -> None:
    """`GET /api/health` returns `200 {"ok": true}`."""
    response = client.get('/api/health')

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'ok': True}


@pytest.mark.parametrize('path', ['/health', '/openapi.json', '/docs', '/docs/oauth2-redirect', '/redoc', '/api/redoc'])
def test_routes_are_only_served_under_the_api_prefix(client: TestClient, path: str) -> None:
    """Without the `/api` prefix there is no route, and FastAPI's default doc paths are disabled."""
    response = client.get(path)

    assert response.status_code == HTTPStatus.NOT_FOUND


def test_every_api_route_is_under_the_api_prefix() -> None:
    """Every route in the module-level app's OpenAPI document lives under `/api`.

    The docs routes are left out of the document; `tests/api/test_docs.py` covers their paths.
    """
    api_paths = list(app.openapi()['paths'])

    assert api_paths
    for path in api_paths:
        assert path.startswith('/api/'), path


def test_openapi_document_describes_health(client: TestClient) -> None:
    """`/api/openapi.json` lists `/api/health` with the `HealthResponse` schema."""
    response = client.get('/api/openapi.json')

    assert response.status_code == HTTPStatus.OK
    document = response.json()
    health = document['paths']['/api/health']['get']['responses']['200']
    assert health['content']['application/json']['schema'] == {'$ref': '#/components/schemas/HealthResponse'}
    assert document['components']['schemas']['HealthResponse']['properties']['ok']['const'] is True
