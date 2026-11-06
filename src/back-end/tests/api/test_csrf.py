"""Tests for the `Content-Type: application/json` requirement on mutating routes (spec §8 CSRF)."""

from http import HTTPStatus

import pytest
from fastapi.testclient import TestClient

from budge.api.csrf import MUTATING_METHODS, is_json
from tests.api.test_routes import APP_OPERATIONS, request_path

MUTATING_OPERATIONS = [(method, path) for method, path in APP_OPERATIONS if method in MUTATING_METHODS]
"""Every mutating `(method, path)` the app serves."""


def test_the_app_has_mutating_routes() -> None:
    """The parametrized check below can't pass vacuously."""
    assert ('POST', '/api/auth/session') in MUTATING_OPERATIONS
    assert ('DELETE', '/api/auth/session') in MUTATING_OPERATIONS


FORM_CONTENT_TYPES = [None, 'text/plain', 'application/x-www-form-urlencoded', 'multipart/form-data']
"""No `Content-Type`, and each one a cross-site HTML form can send without a CORS preflight."""


@pytest.mark.parametrize(('method', 'path'), MUTATING_OPERATIONS)
@pytest.mark.parametrize('content_type', FORM_CONTENT_TYPES)
def test_every_mutating_route_requires_json(
    client: TestClient, method: str, path: str, content_type: str | None
) -> None:
    """Every mutating route answers `415 invalid_request` without a JSON `Content-Type`, as a form post would send."""
    headers = {'content-type': content_type} if content_type else {}

    response = client.request(method, request_path(path), headers=headers)

    assert response.status_code == HTTPStatus.UNSUPPORTED_MEDIA_TYPE
    assert response.json()['error'] == {
        'code': 'invalid_request',
        'message': f'{method} requests must have the header Content-Type: application/json.',
    }


@pytest.mark.parametrize(
    ('content_type', 'expected'),
    [
        ('application/json', True),
        ('application/json; charset=utf-8', True),
        ('APPLICATION/JSON', True),
        ('application/jsonx', False),
        ('application/vnd.api+json', False),
        ('text/plain', False),
        ('', False),
        (None, False),
    ],
)
def test_is_json(content_type: str | None, expected: bool) -> None:
    """Only `application/json` itself counts, with any parameters."""
    assert is_json(content_type) is expected
