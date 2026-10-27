"""The API's single error envelope, `{"error": {"code", "message"}}`, for every error response (spec §8 Errors).

`install_error_handlers` replaces FastAPI's and Starlette's default error bodies, including the request-validation
`422 {"detail": [...]}`, so each error a route raises, an unknown path, and an unhandled exception all answer with the
envelope. Routes raise `APIError` to choose the `code`; a plain `HTTPException` gets the default code for its status.
`error_responses` documents the envelope in the OpenAPI document, so the generated client knows the error shape.
"""

import logging
from collections.abc import Mapping, Sequence
from http import HTTPStatus
from typing import Any, Final, Literal, cast

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict
from starlette.exceptions import HTTPException as StarletteHTTPException

__all__ = [
    'DEFAULT_CODES',
    'APIError',
    'ErrorCode',
    'ErrorDetail',
    'ErrorResponse',
    'default_code',
    'error_response',
    'error_responses',
    'install_error_handlers',
    'validation_message',
]

logger = logging.getLogger(__name__)

ErrorCode = Literal[
    'unauthenticated',
    'not_allowlisted',
    'not_found',
    'duplicate_account',
    'lease_held',
    'invalid_request',
    'plaid_error',
    'internal_error',
]
"""Every error `code` the API answers with (spec §8 Errors)."""

DEFAULT_CODES: Final[Mapping[int, ErrorCode]] = {
    HTTPStatus.UNAUTHORIZED: 'unauthenticated',
    HTTPStatus.FORBIDDEN: 'not_allowlisted',
    HTTPStatus.NOT_FOUND: 'not_found',
    status.HTTP_422_UNPROCESSABLE_CONTENT: 'invalid_request',
}
"""The `code` for an error raised without one, by status; see `default_code` for the rest."""


class ErrorDetail(BaseModel):
    """The `error` member of an error response."""

    model_config = ConfigDict(extra='forbid', strict=True, use_attribute_docstrings=True)

    code: ErrorCode
    """A stable, machine-readable error code; the SPA branches on it (e.g. `unauthenticated` shows sign-in)."""

    message: str
    """A human-readable description of the error, not meant for parsing."""


class ErrorResponse(BaseModel):
    """The body of every error response: `{"error": {"code", "message"}}`."""

    model_config = ConfigDict(extra='forbid', strict=True, use_attribute_docstrings=True)

    error: ErrorDetail
    """What went wrong."""


class APIError(HTTPException):
    """An error response with an explicit `code`, e.g. `APIError(403, 'not_allowlisted', 'not on the allowlist')`.

    >>> error = APIError(HTTPStatus.UNAUTHORIZED, 'unauthenticated', 'no session')
    >>> error.status_code, error.code, error.detail
    (401, 'unauthenticated', 'no session')
    """

    code: ErrorCode
    """The envelope's `code`."""

    def __init__(
        self, status_code: int, code: ErrorCode, message: str, *, headers: Mapping[str, str] | None = None
    ) -> None:
        """Create the error.

        Args:
            status_code: The HTTP status to answer with.
            code: The envelope's `code`.
            message: The envelope's `message`, also the exception's `detail`.
            headers: Extra response headers.
        """
        super().__init__(status_code=int(status_code), detail=message, headers=headers)
        self.code = code


def default_code(status_code: int) -> ErrorCode:
    """Return the `code` for an error raised without one: `DEFAULT_CODES`, else by status class.

    Any other `4xx` (such as `405` or `415`) is `invalid_request`, and any `5xx` is `internal_error`.

    >>> default_code(404), default_code(405), default_code(503)
    ('not_found', 'invalid_request', 'internal_error')
    """
    if status_code in DEFAULT_CODES:
        return DEFAULT_CODES[status_code]
    return 'internal_error' if status_code >= HTTPStatus.INTERNAL_SERVER_ERROR else 'invalid_request'


def error_response(
    status_code: int, code: ErrorCode, message: str, *, headers: Mapping[str, str] | None = None
) -> JSONResponse:
    """Build an error response with the envelope body.

    >>> error_response(404, 'not_found', 'no such connection').body
    b'{"error":{"code":"not_found","message":"no such connection"}}'
    """
    body = ErrorResponse(error=ErrorDetail(code=code, message=message))
    return JSONResponse(body.model_dump(mode='json'), status_code=status_code, headers=headers)


def validation_message(errors: Sequence[Mapping[str, Any]]) -> str:  # Any: FastAPI types each error as `Any`
    """Summarize request-validation errors as one line: `<location>: <message>` per error, joined by `; `.

    >>> validation_message([{'loc': ('body', 'credential'), 'msg': 'Field required'}])
    'body.credential: Field required'
    """
    return '; '.join(f'{".".join(str(part) for part in error["loc"])}: {error["msg"]}' for error in errors)


async def _http_exception(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Render an `HTTPException` (FastAPI's, Starlette's, or `APIError`) with the envelope."""
    code = exc.code if isinstance(exc, APIError) else default_code(exc.status_code)
    # Starlette types `detail` as `str`, but FastAPI's `HTTPException` accepts any JSON value there
    detail = cast('object', exc.detail)
    message = detail if isinstance(detail, str) else HTTPStatus(exc.status_code).phrase
    return error_response(exc.status_code, code, message, headers=exc.headers)


async def _validation_error(_request: Request, exc: RequestValidationError) -> JSONResponse:
    """Render a request-validation error as `422 invalid_request`, replacing FastAPI's `{"detail": [...]}`."""
    return error_response(status.HTTP_422_UNPROCESSABLE_CONTENT, 'invalid_request', validation_message(exc.errors()))


async def _unhandled_error(_request: Request, exc: Exception) -> JSONResponse:
    """Render any other exception as `500 internal_error`, without leaking its text."""
    logger.error('unhandled error', exc_info=exc)
    return error_response(HTTPStatus.INTERNAL_SERVER_ERROR, 'internal_error', 'Internal server error')


def install_error_handlers(app: FastAPI) -> None:
    """Make every error response from `app` use the envelope.

    >>> from fastapi.testclient import TestClient
    >>> app = FastAPI()
    >>> install_error_handlers(app)
    >>> TestClient(app).get('/nowhere').json()
    {'error': {'code': 'not_found', 'message': 'Not Found'}}
    """
    # through `exception_handler`, whose decorator type accepts each handler's narrower exception parameter
    app.exception_handler(StarletteHTTPException)(_http_exception)
    app.exception_handler(RequestValidationError)(_validation_error)
    app.exception_handler(Exception)(_unhandled_error)


def error_responses(*statuses: int) -> dict[int | str, dict[str, Any]]:  # Any: FastAPI's `responses=` value type
    """Document the envelope for each status, for a route's or router's `responses=`.

    >>> error_responses(401)
    {401: {'model': <class 'budge.api.errors.ErrorResponse'>, 'description': 'Unauthorized'}}
    """
    return {code: {'model': ErrorResponse, 'description': HTTPStatus(code).phrase} for code in statuses}
