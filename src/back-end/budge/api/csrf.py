"""CSRF defence for mutating routes: they require `Content-Type: application/json` (spec §8 Auth, CSRF).

The session cookie is `SameSite=Strict` and the SPA is served from the API's own origin, which is enough for v1. As a
second layer, every mutating request must declare a JSON body. A cross-site HTML form can only send
`application/x-www-form-urlencoded`, `multipart/form-data` or `text/plain`, and setting `application/json` cross-site
needs a CORS preflight, which the API never grants.

FastAPI parses a body with no `Content-Type` as JSON, so the check is explicit. Both of `budge.api.routes`' routers
depend on `require_json_for_mutations`, so it covers each mutating route, including ones with no body, such as
`DELETE /api/auth/session`.
"""

from email.message import Message
from http import HTTPStatus
from typing import Final

from fastapi import Request

from budge.api.errors import APIError

__all__ = ['JSON_MEDIA_TYPE', 'MUTATING_METHODS', 'is_json', 'require_json_for_mutations']

JSON_MEDIA_TYPE: Final = 'application/json'
"""The media type every mutating request must declare."""

MUTATING_METHODS: Final = frozenset({'POST', 'PUT', 'PATCH', 'DELETE'})
"""The HTTP methods that change state, and so require `JSON_MEDIA_TYPE`."""


def is_json(content_type: str | None) -> bool:
    """Return whether a `Content-Type` header names `application/json`, ignoring case and parameters.

    >>> is_json('Application/JSON; charset=utf-8'), is_json('text/plain'), is_json(None)
    (True, False, False)
    """
    if content_type is None:
        return False
    header = Message()
    header['content-type'] = content_type
    return header.get_content_type() == JSON_MEDIA_TYPE


def require_json_for_mutations(request: Request) -> None:
    """Reject a mutating request whose `Content-Type` isn't `application/json` with `415 invalid_request`.

    Args:
        request: The incoming request.

    Raises:
        APIError: `415 invalid_request` for a `POST`, `PUT`, `PATCH` or `DELETE` without a JSON `Content-Type`.
    """
    if request.method in MUTATING_METHODS and not is_json(request.headers.get('content-type')):
        raise APIError(
            HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
            'invalid_request',
            f'{request.method} requests must have the header Content-Type: {JSON_MEDIA_TYPE}.',
        )
