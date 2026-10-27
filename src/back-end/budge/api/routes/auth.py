"""`POST /api/auth/session` (sign in with Google) and `DELETE /api/auth/session` (sign out) (spec §8 Auth).

Sign-in is one of the two routes that need no session, so `budge.api.routes.open_router` includes `sign_in_router`.
Sign-out requires one, like every other route, so `budge.api.routes.protected_router` includes `router`.
"""

import logging
from http import HTTPStatus
from typing import Annotated

import jwt
from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel, ConfigDict

from budge.api.auth import (
    BROWSER_SESSION_LIFETIME,
    REMEMBER_ME_LIFETIME,
    SESSION_COOKIE,
    SESSION_COOKIE_PATH,
    get_google_jwks,
    get_session_key,
    issue_session_token,
    not_allowlisted,
    verify_google_credential,
)
from budge.api.config import AuthSettings, get_auth_settings
from budge.api.errors import error_responses

__all__ = ['SessionRequest', 'create_session', 'delete_session', 'router', 'set_session_cookie', 'sign_in_router']

logger = logging.getLogger(__name__)

sign_in_router = APIRouter(tags=['auth'])
"""The sign-in route; included under `/api` by `budge.api.routes.open_router`, so it needs no session."""

router = APIRouter(tags=['auth'])
"""The sign-out route; included under `/api` by `budge.api.routes.protected_router`, so it requires a session."""


class SessionRequest(BaseModel):
    """The `POST /api/auth/session` request body."""

    model_config = ConfigDict(extra='forbid', strict=True, use_attribute_docstrings=True)

    credential: str
    """The Google ID token from Google Identity Services (the sign-in button or One Tap)."""

    remember_me: bool
    """Keep the session for 30 days; otherwise it ends when the browser closes, and after 12 hours at most."""


def set_session_cookie(response: Response, token: str, *, remember_me: bool) -> None:
    """Set the `budge_session` cookie: `HttpOnly; Secure; SameSite=Strict; Path=/api` (spec §8).

    With `remember_me` the cookie lasts `REMEMBER_ME_LIFETIME` (`Max-Age`); without it, it's a browser-session cookie.

    >>> response = Response()
    >>> set_session_cookie(response, 'token', remember_me=False)
    >>> response.headers['set-cookie']
    'budge_session=token; HttpOnly; Path=/api; SameSite=strict; Secure'
    """
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=int(REMEMBER_ME_LIFETIME.total_seconds()) if remember_me else None,
        path=SESSION_COOKIE_PATH,
        secure=True,
        httponly=True,
        samesite='strict',
    )


# FastAPI publishes a route function's docstring as the operation's OpenAPI `description`, so pass `description=`
@sign_in_router.post(
    '/auth/session',
    status_code=HTTPStatus.NO_CONTENT,
    response_class=Response,
    responses=error_responses(
        HTTPStatus.UNAUTHORIZED,
        HTTPStatus.FORBIDDEN,
        HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
        status.HTTP_422_UNPROCESSABLE_CONTENT,
    ),
    description=(
        'Sign in with a Google ID token and set the `budge_session` cookie. '
        '`401 unauthenticated` if the token is invalid or expired; '
        '`403 not_allowlisted` if the Google account is not on the allowlist.'
    ),
)
def create_session(
    body: SessionRequest,
    settings: Annotated[AuthSettings, Depends(get_auth_settings)],
    key: Annotated[str, Depends(get_session_key)],
    jwks: Annotated[jwt.PyJWKClient, Depends(get_google_jwks)],
) -> Response:
    """Verify the Google credential, check its `sub` against the allowlist, and start a session.

    A rejected `sub` is logged (`extra={'sub': ...}`) so the owner can add it to the allowlist (spec §8 bootstrap).
    """
    claims = verify_google_credential(body.credential, client_id=settings.google_client_id, jwks=jwks)
    if claims.sub not in settings.allowed_subs:
        logger.warning('sign-in rejected: Google sub %s is not on the allowlist', claims.sub, extra={'sub': claims.sub})
        raise not_allowlisted()

    lifetime = REMEMBER_ME_LIFETIME if body.remember_me else BROWSER_SESSION_LIFETIME
    token = issue_session_token(claims.sub, key=key, lifetime=lifetime)
    response = Response(status_code=HTTPStatus.NO_CONTENT)
    set_session_cookie(response, token, remember_me=body.remember_me)
    return response


@router.delete(
    '/auth/session',
    status_code=HTTPStatus.NO_CONTENT,
    response_class=Response,
    responses=error_responses(HTTPStatus.UNSUPPORTED_MEDIA_TYPE),
    description='Sign out: clear the `budge_session` cookie.',
)
def delete_session() -> Response:
    """Sign out by clearing the session cookie (with the same attributes it was set with).

    >>> delete_session().headers['set-cookie']  # doctest: +ELLIPSIS
    'budge_session=""; expires=...; HttpOnly; Max-Age=0; Path=/api; SameSite=strict; Secure'
    """
    response = Response(status_code=HTTPStatus.NO_CONTENT)
    response.delete_cookie(SESSION_COOKIE, path=SESSION_COOKIE_PATH, secure=True, httponly=True, samesite='strict')
    return response
