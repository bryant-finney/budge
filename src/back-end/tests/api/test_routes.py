"""Tests for the API's two routers: `open_router` (public) and `protected_router` (session required) (spec §8)."""

import re
from collections.abc import Sequence
from http import HTTPStatus

import pytest
from fastapi.routing import iter_route_contexts
from fastapi.testclient import TestClient
from starlette.routing import BaseRoute

from budge.api.app import app, create_app
from budge.api.routes import open_router
from tests.fakes import SESSION_DENIED

PATH_PARAM = re.compile(r'\{[^}]+\}')
"""A path parameter in a route's path, such as `{connection_id}`."""


def operations(routes: Sequence[BaseRoute]) -> list[tuple[str, str]]:
    """Return every `(method, path)` the routes serve, descending into included routers."""
    return sorted(
        (method, context.path)
        for context in iter_route_contexts(routes)
        if context.path is not None
        for method in context.methods or ()
    )


APP_OPERATIONS = operations(app.routes)
"""Every `(method, path)` the module-level app serves."""

OPEN_OPERATIONS = frozenset(operations(open_router.routes))
"""The `(method, path)` pairs served without a session."""


def request_path(path: str) -> str:
    """Fill each path parameter in a route's path with `1`, so the route matches a request."""
    return PATH_PARAM.sub('1', path)


def test_open_router_holds_only_health_and_sign_in() -> None:
    """Only `GET /api/health` and `POST /api/auth/session` are public (spec §8); any other has to change this test.

    `DELETE /api/auth/session` (sign-out) still requires a session, so it stays on `protected_router`.
    """
    assert OPEN_OPERATIONS == {('GET', '/api/health'), ('POST', '/api/auth/session')}


def test_route_walk_finds_every_route() -> None:
    """The walk descends into included routers, so the parametrized checks below can't pass vacuously."""
    assert ('GET', '/api/health') in APP_OPERATIONS
    assert ('GET', '/api/openapi.json') in APP_OPERATIONS
    assert len(APP_OPERATIONS) > len(OPEN_OPERATIONS)


@pytest.mark.parametrize(('method', 'path'), APP_OPERATIONS)
def test_session_gates_every_route_but_the_open_ones(denied_client: TestClient, method: str, path: str) -> None:
    """With `require_session` failing, the session check refuses every route off `open_router`, and none on it.

    An open route may still answer `4xx` for its own reasons (such as an empty request body), so the check is that the
    session gate's own refusal never reaches it, not that it answers `200`.
    """
    response = denied_client.request(method, request_path(path))

    if (method, path) in OPEN_OPERATIONS:
        assert SESSION_DENIED not in response.text
    else:
        assert response.status_code == HTTPStatus.UNAUTHORIZED
        assert SESSION_DENIED in response.text


@pytest.mark.parametrize(('method', 'path'), APP_OPERATIONS)
def test_allowlisted_session_reaches_every_route(client: TestClient, method: str, path: str) -> None:
    """A signed-in, allowlisted session passes the session check on every route.

    Passing means not refused for want of a session; a route may still reject an empty request body or content type.
    """
    status = client.request(method, request_path(path)).status_code

    assert status not in {HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN}


@pytest.mark.parametrize(('method', 'path'), APP_OPERATIONS)
def test_real_session_check_gates_every_route_but_the_open_ones(
    anonymous_client: TestClient, method: str, path: str
) -> None:
    """Without a cookie, the real `require_session` answers `401 unauthenticated` everywhere but the open routes."""
    response = anonymous_client.request(method, request_path(path))

    if (method, path) in OPEN_OPERATIONS:
        assert response.status_code != HTTPStatus.UNAUTHORIZED
    else:
        assert response.status_code == HTTPStatus.UNAUTHORIZED
        assert response.json()['error']['code'] == 'unauthenticated'


def test_overrides_stay_on_their_own_app(denied_client: TestClient, client: TestClient) -> None:
    """Overriding `require_session` on one app leaves the module-level `app` and other new apps unchanged."""
    assert denied_client.get('/api/docs').status_code == HTTPStatus.UNAUTHORIZED
    assert client.get('/api/docs').status_code == HTTPStatus.OK
    assert not app.dependency_overrides
    assert not create_app().dependency_overrides


def test_request_path_fills_path_parameters() -> None:
    """Each path parameter is filled, whatever its converter, and a path without any is unchanged."""
    assert request_path('/api/connections/{connection_id}/items/{item:int}') == '/api/connections/1/items/1'
    assert request_path('/api/health') == '/api/health'
