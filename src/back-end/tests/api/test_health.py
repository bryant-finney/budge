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


def test_every_route_is_under_the_api_prefix() -> None:
    """Every route the module-level app serves, docs included, lives under `/api`.

    The API routes are read from the OpenAPI document and the doc routes from the app's settings, since FastAPI's
    `app.routes` holds included routers as private wrapper objects without a `path`.
    """
    api_paths = list(app.openapi()['paths'])
    doc_paths = [app.openapi_url, app.docs_url, app.swagger_ui_oauth2_redirect_url]

    assert api_paths
    assert app.redoc_url is None
    for path in [*api_paths, *doc_paths]:
        assert path is not None
        assert path.startswith('/api/'), path


def test_openapi_document_describes_health(client: TestClient) -> None:
    """`/api/openapi.json` lists `/api/health` with the `HealthResponse` schema."""
    response = client.get('/api/openapi.json')

    assert response.status_code == HTTPStatus.OK
    document = response.json()
    health = document['paths']['/api/health']['get']['responses']['200']
    assert health['content']['application/json']['schema'] == {'$ref': '#/components/schemas/HealthResponse'}
    assert document['components']['schemas']['HealthResponse']['properties']['ok']['const'] is True


def test_docs_are_served_under_the_api_prefix(client: TestClient) -> None:
    """Swagger UI is served at `/api/docs` and loads the prefixed OpenAPI document."""
    response = client.get('/api/docs')

    assert response.status_code == HTTPStatus.OK
    assert '/api/openapi.json' in response.text
    assert '/api/docs/oauth2-redirect' in response.text


def test_docs_oauth2_redirect_is_served_under_the_api_prefix(client: TestClient) -> None:
    """Swagger UI's OAuth2 redirect page is reachable through CloudFront's `/api/*` behavior."""
    response = client.get('/api/docs/oauth2-redirect')

    assert response.status_code == HTTPStatus.OK
