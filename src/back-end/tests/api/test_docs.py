"""Tests for the OpenAPI document and Swagger UI routes in `budge.api.routes.docs` (spec §8)."""

import re
from http import HTTPStatus

import pytest
from fastapi.testclient import TestClient

from budge.api.app import app, create_app
from budge.api.routes import docs
from tests.auth import client_for, configure, session_token

DOCS_URLS = ['/api/openapi.json', '/api/docs', '/api/docs/oauth2-redirect', '/api/redoc']
"""Every docs route's full path."""

HTML_URLS = ['/api/docs', '/api/docs/oauth2-redirect', '/api/redoc']
"""The docs routes that serve an HTML page."""

EXTERNAL_URL = re.compile(r'https?://[^\s"\'<>]+')
"""Any absolute `http(s)` URL in a page's source."""

PINNED_CDN_URL = re.compile(r'https://cdn\.jsdelivr\.net/npm/[a-z][a-z0-9-]*@\d+\.\d+\.\d+/\S+')
"""A `cdn.jsdelivr.net` URL that names an exact `major.minor.patch` npm release, never a floating tag."""


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

    assert sorted(paths) == ['/api/auth/session', '/api/health']


def test_openapi_document_lists_the_root_path_as_a_server() -> None:
    """Under an ASGI `root_path`, the document lists it first in `servers`, as FastAPI's built-in route does."""
    with client_for(configure(create_app()), token=session_token(), root_path='/stage') as test_client:
        document = test_client.get('/api/openapi.json').json()

    assert document['servers'] == [{'url': '/stage'}]


def test_openapi_document_does_not_duplicate_a_listed_root_path() -> None:
    """A `root_path` already in `servers` is not listed twice."""
    application = configure(create_app())
    application.servers = [{'url': '/stage'}]
    with client_for(application, token=session_token(), root_path='/stage') as test_client:
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


def test_swagger_ui_loads_the_pinned_assets(client: TestClient) -> None:
    """Swagger UI loads its JavaScript and CSS from the pinned `swagger-ui-dist` release, with no remote favicon."""
    text = client.get('/api/docs').text

    assert f'<script src="{docs.SWAGGER_UI_JS_URL}"></script>' in text
    assert f'<link type="text/css" rel="stylesheet" href="{docs.SWAGGER_UI_CSS_URL}">' in text
    assert f'<link rel="shortcut icon" href="{docs.FAVICON_URL}">' in text


def test_swagger_ui_prefixes_the_root_path() -> None:
    """Under an ASGI `root_path`, Swagger UI's document and redirect URLs carry it."""
    with client_for(configure(create_app()), token=session_token(), root_path='/stage') as test_client:
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


def test_redoc_loads_the_pinned_assets(client: TestClient) -> None:
    """ReDoc loads its JavaScript from the pinned `redoc` release, with no remote favicon and no Google Fonts."""
    text = client.get('/api/redoc').text

    assert f'<script src="{docs.REDOC_JS_URL}"> </script>' in text
    assert f'<link rel="shortcut icon" href="{docs.FAVICON_URL}">' in text


@pytest.mark.parametrize('url', HTML_URLS)
def test_docs_pages_load_only_exact_cdn_releases(client: TestClient, url: str) -> None:
    """Every remote URL a docs page names is an exact-version `cdn.jsdelivr.net` asset, so nothing floats."""
    text = client.get(url).text

    assert [external for external in EXTERNAL_URL.findall(text) if not PINNED_CDN_URL.fullmatch(external)] == []
    assert 'fastapi.tiangolo.com' not in text
    assert 'fonts.googleapis.com' not in text


def test_redoc_prefixes_the_root_path() -> None:
    """Under an ASGI `root_path`, ReDoc's document URL carries it."""
    with client_for(configure(create_app()), token=session_token(), root_path='/stage') as test_client:
        text = test_client.get('/api/redoc').text

    assert '<redoc spec-url="/stage/api/openapi.json"></redoc>' in text


@pytest.mark.parametrize('url', DOCS_URLS)
def test_session_gates_every_docs_route(denied_client: TestClient, url: str) -> None:
    """The docs routes sit on `protected_router`, so each one requires a session (spec §8)."""
    assert denied_client.get(url).status_code == HTTPStatus.UNAUTHORIZED


@pytest.mark.parametrize('url', DOCS_URLS)
def test_docs_need_a_session(anonymous_client: TestClient, url: str) -> None:
    """Without a session cookie, each docs route answers `401 unauthenticated` (PR #26 review, #29)."""
    response = anonymous_client.get(url)

    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.json()['error']['code'] == 'unauthenticated'


@pytest.mark.parametrize('url', DOCS_URLS)
def test_docs_need_an_allowlisted_session(outsider_client: TestClient, url: str) -> None:
    """With a valid session for a `sub` that isn't allowlisted, each docs route answers `403 not_allowlisted`."""
    response = outsider_client.get(url)

    assert response.status_code == HTTPStatus.FORBIDDEN
    assert response.json()['error']['code'] == 'not_allowlisted'


@pytest.mark.parametrize('url', DOCS_URLS)
def test_docs_are_served_to_an_allowlisted_session(client: TestClient, url: str) -> None:
    """With an allowlisted session, each docs route answers `200`: JSON for the document, HTML for the pages."""
    response = client.get(url)

    assert response.status_code == HTTPStatus.OK
    expected = 'application/json' if url.endswith('.json') else 'text/html; charset=utf-8'
    assert response.headers['content-type'] == expected


def test_openapi_is_generated_offline_without_a_session() -> None:
    """`app.openapi()` builds the full document with no request, so generating the SPA's types needs no session."""
    document = create_app().openapi()

    assert sorted(document['paths']) == ['/api/auth/session', '/api/health']


def test_session_leaves_health_open(denied_client: TestClient) -> None:
    """`GET /api/health` sits on `open_router`, so it stays unauthenticated when sessions fail (spec §8)."""
    response = denied_client.get('/api/health')

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'ok': True}
