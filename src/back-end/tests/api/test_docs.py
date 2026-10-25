"""Tests for the OpenAPI document and Swagger UI routes in `budge.api.routes.docs` (spec §8)."""

from collections.abc import Iterator
from http import HTTPStatus
from typing import NoReturn

import pytest
from fastapi import Depends, FastAPI, HTTPException
from fastapi.testclient import TestClient

from budge.api.app import app, create_app
from budge.api.routes import API_PREFIX, docs

DOCS_URLS = [f'{API_PREFIX}{path}' for path in (docs.OPENAPI_PATH, docs.DOCS_PATH, docs.OAUTH2_REDIRECT_PATH)]
"""Every docs route's full path."""


def _deny() -> NoReturn:
    """Stand in for the auth PR's session dependency by rejecting every request."""
    raise HTTPException(status_code=HTTPStatus.UNAUTHORIZED)


@pytest.fixture
def gated_client() -> Iterator[TestClient]:
    """A client for an app whose docs hook holds a dependency that rejects every request."""
    with TestClient(create_app(docs_dependencies=[Depends(_deny)])) as test_client:
        yield test_client


def test_builtin_doc_routes_are_off() -> None:
    """FastAPI's own doc routes are disabled, so `budge.api.routes.docs` alone serves the docs."""
    assert app.openapi_url is None
    assert app.docs_url is None
    assert app.redoc_url is None
    assert app.swagger_ui_oauth2_redirect_url is None


def test_docs_hook_is_empty_until_auth() -> None:
    """The docs are public until the auth PR adds its session dependency to the hook (spec §8)."""
    assert not docs.DOCS_DEPENDENCIES


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


@pytest.mark.parametrize('url', DOCS_URLS)
def test_docs_hook_gates_every_docs_route(gated_client: TestClient, url: str) -> None:
    """A dependency in the docs hook applies to every docs route."""
    assert gated_client.get(url).status_code == HTTPStatus.UNAUTHORIZED


def test_docs_hook_leaves_health_open(gated_client: TestClient) -> None:
    """The docs hook doesn't reach `GET /api/health`, which stays unauthenticated (spec §8)."""
    response = gated_client.get('/api/health')

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'ok': True}


def test_docs_hook_does_not_change_the_module_router() -> None:
    """Building a gated app leaves the shared docs router, and so the default app, ungated."""
    gated: FastAPI = create_app(docs_dependencies=[Depends(_deny)])

    assert gated.openapi() == app.openapi()
    assert not docs.router.dependencies
    with TestClient(create_app()) as test_client:
        assert test_client.get('/api/docs').status_code == HTTPStatus.OK
