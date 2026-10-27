"""Tests for the OpenAPI document and Swagger UI routes in `budge.api.routes.docs` (spec §8)."""

from http import HTTPStatus

import pytest
from fastapi.testclient import TestClient

from budge.api.app import app, create_app
from budge.api.routes import API_PREFIX, docs

DOCS_URLS = [
    f'{API_PREFIX}{path}' for path in (docs.OPENAPI_PATH, docs.DOCS_PATH, docs.OAUTH2_REDIRECT_PATH, docs.REDOC_PATH)
]
"""Every docs route's full path."""


def test_builtin_doc_routes_are_off() -> None:
    """FastAPI's own doc routes are disabled, so `budge.api.routes.docs` alone serves the docs."""
    assert app.openapi_url is None
    assert app.docs_url is None
    assert app.redoc_url is None
    assert app.swagger_ui_oauth2_redirect_url is None


def test_openapi_document_is_the_apps_schema(client: TestClient) -> None:
    """`/api/openapi.json` serves `app.openapi()` unchanged, so offline schema generation matches what's served."""
    response = client.get('/api/openapi.json')

    assert response.status_code == HTTPStatus.OK
    assert response.headers['content-type'] == 'application/json'
    assert response.json() == create_app().openapi()


def test_openapi_document_leaves_out_the_docs_routes(client: TestClient) -> None:
    """The docs routes stay out of the OpenAPI document, which lists only the API's own routes."""
    paths = client.get('/api/openapi.json').json()['paths']

    assert sorted(paths) == ['/api/health']


def test_openapi_document_lists_the_root_path_as_a_server() -> None:
    """Under an ASGI `root_path`, the document lists it first in `servers`, as FastAPI's built-in route does."""
    with TestClient(create_app(), root_path='/stage') as test_client:
        document = test_client.get('/api/openapi.json').json()

    assert document['servers'] == [{'url': '/stage'}]


def test_openapi_document_does_not_duplicate_a_listed_root_path() -> None:
    """A `root_path` already in `servers` is not listed twice."""
    application = create_app()
    application.servers = [{'url': '/stage'}]
    with TestClient(application, root_path='/stage') as test_client:
        document = test_client.get('/api/openapi.json').json()

    assert document['servers'] == [{'url': '/stage'}]


def test_openapi_document_omits_servers_without_a_root_path(client: TestClient) -> None:
    """With no `root_path` the document has no `servers` entry."""
    assert 'servers' not in client.get('/api/openapi.json').json()


def test_swagger_ui_loads_the_prefixed_document(client: TestClient) -> None:
    """`/api/docs` serves Swagger UI HTML that loads `/api/openapi.json` and uses the prefixed redirect page."""
    response = client.get('/api/docs')

    assert response.status_code == HTTPStatus.OK
    assert response.headers['content-type'] == 'text/html; charset=utf-8'
    assert "url: '/api/openapi.json'" in response.text
    assert "oauth2RedirectUrl: window.location.origin + '/api/docs/oauth2-redirect'" in response.text
    assert '<title>budge - Swagger UI</title>' in response.text


def test_swagger_ui_prefixes_the_root_path() -> None:
    """Under an ASGI `root_path`, Swagger UI's document and redirect URLs carry it."""
    with TestClient(create_app(), root_path='/stage') as test_client:
        text = test_client.get('/api/docs').text

    assert "url: '/stage/api/openapi.json'" in text
    assert "'/stage/api/docs/oauth2-redirect'" in text


def test_oauth2_redirect_page_is_served(client: TestClient) -> None:
    """`/api/docs/oauth2-redirect` serves Swagger UI's OAuth2 redirect page."""
    response = client.get('/api/docs/oauth2-redirect')

    assert response.status_code == HTTPStatus.OK
    assert response.headers['content-type'] == 'text/html; charset=utf-8'
    assert 'oauth2' in response.text


def test_redoc_loads_the_prefixed_document(client: TestClient) -> None:
    """`/api/redoc` serves ReDoc HTML that loads `/api/openapi.json`."""
    response = client.get('/api/redoc')

    assert response.status_code == HTTPStatus.OK
    assert response.headers['content-type'] == 'text/html; charset=utf-8'
    assert '<redoc spec-url="/api/openapi.json"></redoc>' in response.text
    assert '<title>budge - ReDoc</title>' in response.text


def test_redoc_prefixes_the_root_path() -> None:
    """Under an ASGI `root_path`, ReDoc's document URL carries it."""
    with TestClient(create_app(), root_path='/stage') as test_client:
        text = test_client.get('/api/redoc').text

    assert '<redoc spec-url="/stage/api/openapi.json"></redoc>' in text


@pytest.mark.parametrize('url', DOCS_URLS)
def test_session_gates_every_docs_route(denied_client: TestClient, url: str) -> None:
    """The docs routes sit on `protected_router`, so each one requires a session (spec §8)."""
    assert denied_client.get(url).status_code == HTTPStatus.UNAUTHORIZED


def test_session_leaves_health_open(denied_client: TestClient) -> None:
    """`GET /api/health` sits on `open_router`, so it stays unauthenticated when sessions fail (spec §8)."""
    response = denied_client.get('/api/health')

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'ok': True}
