"""Tests for `GET /api/health` and the `/api`-prefixed OpenAPI document (spec §4, §8)."""

from http import HTTPStatus

import httpx
import pytest

from budge.api.app import app

pytestmark = pytest.mark.anyio


async def test_health_returns_ok(client: httpx.AsyncClient) -> None:
    """`GET /api/health` returns `200 {"ok": true}`."""
    response = await client.get('/api/health')

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'ok': True}


@pytest.mark.parametrize('path', ['/health', '/openapi.json', '/docs', '/docs/oauth2-redirect', '/redoc', '/api/redoc'])
async def test_routes_are_only_served_under_the_api_prefix(client: httpx.AsyncClient, path: str) -> None:
    """Without the `/api` prefix there is no route, and FastAPI's default doc paths are disabled."""
    response = await client.get(path)

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


async def test_openapi_document_describes_health(client: httpx.AsyncClient) -> None:
    """`/api/openapi.json` lists `/api/health` with the `HealthResponse` schema."""
    response = await client.get('/api/openapi.json')

    assert response.status_code == HTTPStatus.OK
    document = response.json()
    health = document['paths']['/api/health']['get']['responses']['200']
    assert health['content']['application/json']['schema'] == {'$ref': '#/components/schemas/HealthResponse'}
    assert document['components']['schemas']['HealthResponse']['properties']['ok']['const'] is True


async def test_docs_are_served_under_the_api_prefix(client: httpx.AsyncClient) -> None:
    """Swagger UI is served at `/api/docs` and loads the prefixed OpenAPI document."""
    response = await client.get('/api/docs')

    assert response.status_code == HTTPStatus.OK
    assert '/api/openapi.json' in response.text
    assert '/api/docs/oauth2-redirect' in response.text


async def test_docs_oauth2_redirect_is_served_under_the_api_prefix(client: httpx.AsyncClient) -> None:
    """Swagger UI's OAuth2 redirect page is reachable through CloudFront's `/api/*` behavior."""
    response = await client.get('/api/docs/oauth2-redirect')

    assert response.status_code == HTTPStatus.OK
