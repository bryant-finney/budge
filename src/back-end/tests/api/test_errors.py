"""Tests for the error envelope, `{"error": {"code", "message"}}`, on every error response (spec §8 Errors)."""

from http import HTTPStatus
from typing import NoReturn

import pytest
from fastapi import FastAPI, HTTPException, status
from fastapi.testclient import TestClient

from budge.api.errors import ErrorResponse, default_code, install_error_handlers


def _dict_detail() -> NoReturn:
    raise HTTPException(status_code=HTTPStatus.CONFLICT, detail={'reason': 'structured'})


def _teapot() -> NoReturn:
    raise HTTPException(status_code=HTTPStatus.IM_A_TEAPOT, detail='short and stout', headers={'x-probe': '1'})


def _item(item_id: int) -> int:
    return item_id


def _crash() -> NoReturn:
    msg = 'secret internals'
    raise RuntimeError(msg)


@pytest.fixture
def errors_client() -> TestClient:
    """A client for a small app with the envelope handlers and routes that fail in each way."""
    application = FastAPI()
    install_error_handlers(application)
    application.add_api_route('/dict-detail', _dict_detail, response_model=None)
    application.add_api_route('/teapot', _teapot, response_model=None)
    application.add_api_route('/crash', _crash, response_model=None)
    application.add_api_route('/items/{item_id}', _item)
    return TestClient(application, raise_server_exceptions=False)


def envelope(code: str, message: str) -> dict[str, object]:
    """The envelope body for `code` and `message`, checked against the `ErrorResponse` model."""
    body: dict[str, object] = {'error': {'code': code, 'message': message}}
    ErrorResponse.model_validate(body)
    return body


def test_unknown_path_is_not_found(client: TestClient) -> None:
    """Starlette's own `404` for an unknown path uses the envelope too."""
    response = client.get('/api/nowhere')

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == envelope('not_found', 'Not Found')


def test_wrong_method_is_an_invalid_request(client: TestClient) -> None:
    """A `405` has no code of its own in §8, so it is `invalid_request`."""
    response = client.put('/api/health', headers={'content-type': 'application/json'})

    assert response.status_code == HTTPStatus.METHOD_NOT_ALLOWED
    assert response.json() == envelope('invalid_request', 'Method Not Allowed')
    assert response.headers['allow'] == 'GET'


def test_non_string_detail_uses_the_status_phrase(errors_client: TestClient) -> None:
    """A structured `detail` isn't leaked as the message; the status phrase stands in."""
    response = errors_client.get('/dict-detail')

    assert response.status_code == HTTPStatus.CONFLICT
    assert response.json() == envelope('invalid_request', 'Conflict')


def test_http_exception_keeps_its_message_and_headers(errors_client: TestClient) -> None:
    """A plain `HTTPException` keeps its `detail` as the message and its headers."""
    response = errors_client.get('/teapot')

    assert response.json() == envelope('invalid_request', 'short and stout')
    assert response.headers['x-probe'] == '1'


def test_unhandled_error_is_an_internal_error(errors_client: TestClient, caplog: pytest.LogCaptureFixture) -> None:
    """Any other exception is `500 internal_error`, logged, and its text never reaches the client."""
    response = errors_client.get('/crash')

    assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
    assert response.json() == envelope('internal_error', 'Internal server error')
    assert 'secret internals' not in response.text
    assert any(record.exc_info and record.name == 'budge.api.errors' for record in caplog.records)


def test_validation_error_is_an_invalid_request(errors_client: TestClient) -> None:
    """Request-validation errors are `422 invalid_request` with a one-line summary, not `{"detail": [...]}`."""
    response = errors_client.get('/items/abc')

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert response.json() == envelope(
        'invalid_request', 'path.item_id: Input should be a valid integer, unable to parse string as an integer'
    )


@pytest.mark.parametrize(
    ('status', 'code'),
    [(401, 'unauthenticated'), (403, 'not_allowlisted'), (404, 'not_found'), (422, 'invalid_request')],
)
def test_default_codes_follow_spec_8(status: int, code: str) -> None:
    """The statuses §8 names get their codes when raised without one."""
    assert default_code(status) == code
