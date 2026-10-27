"""Google sign-in and the `budge_session` cookie, as FastAPI dependencies rather than middleware (spec §8 Auth).

- **Sign-in** (`budge.api.routes.auth`): `verify_google_credential` checks a Google ID token's RS256 signature against
  Google's JWKS, and its `iss`, `aud` and `exp` (with `GOOGLE_LEEWAY`). The route then checks the `sub` against the
  allowlist and issues a session with `issue_session_token`.
- **Session:** the `budge_session` cookie holds an HS256 JWT `{sub, iat, exp}`, signed with the key from the
  `SecretStore`.
- **Every other route:** `budge.api.routes.protected_router` depends on `require_session`. It verifies the cookie's
  signature and `exp`, then re-checks its `sub` against the allowlist, so removing a `sub` revokes its sessions.

Failures use the error envelope: `401 unauthenticated` for a missing, invalid or expired cookie or Google token, and
`403 not_allowlisted` for a valid identity that isn't on the allowlist.

`GOOGLE_JWKS` caches Google's signing keys at module scope, so the API Lambda fetches them once per execution
environment rather than on every sign-in. `budge.api.handler` runs no lifespan, so this can't be a startup hook.
"""

import datetime as dt
from http import HTTPStatus
from typing import Annotated, Final

import jwt
from fastapi import Depends, Security
from fastapi.security import APIKeyCookie
from pydantic import BaseModel, ConfigDict, ValidationError

from budge.api.config import AuthSettings, get_auth_settings, get_secret_store
from budge.api.errors import APIError
from budge.storage import SecretStore

__all__ = [
    'BROWSER_SESSION_LIFETIME',
    'GOOGLE_ALGORITHM',
    'GOOGLE_ISSUERS',
    'GOOGLE_JWKS',
    'GOOGLE_JWKS_LIFESPAN',
    'GOOGLE_JWKS_URI',
    'GOOGLE_LEEWAY',
    'REMEMBER_ME_LIFETIME',
    'SESSION_ALGORITHM',
    'SESSION_COOKIE',
    'SESSION_COOKIE_PATH',
    'GoogleClaims',
    'SessionClaims',
    'get_google_jwks',
    'get_session_key',
    'issue_session_token',
    'not_allowlisted',
    'read_session_token',
    'require_session',
    'session_cookie',
    'unauthenticated',
    'verify_google_credential',
]

SESSION_COOKIE: Final = 'budge_session'
"""The session cookie's name."""

SESSION_COOKIE_PATH: Final = '/api'
"""The session cookie's `Path`: the browser sends it to the API's routes only."""

SESSION_ALGORITHM: Final = 'HS256'
"""The session token's signing algorithm, and the only one accepted when verifying one."""

REMEMBER_ME_LIFETIME: Final = dt.timedelta(days=30)
"""A "remember me" session's lifetime: both the token's `exp` and the cookie's `Max-Age`."""

BROWSER_SESSION_LIFETIME: Final = dt.timedelta(hours=12)
"""Any other session's `exp`. Its cookie has no `Max-Age`, so the browser also drops it when it closes."""

GOOGLE_JWKS_URI: Final = 'https://www.googleapis.com/oauth2/v3/certs'
"""Google's JSON Web Key Set: the public keys that sign Google ID tokens."""

GOOGLE_JWKS_LIFESPAN: Final = 3600
"""How long, in seconds, the fetched key set is reused. A token signed by a key not in it triggers a refetch."""

GOOGLE_ISSUERS: Final = frozenset({'accounts.google.com', 'https://accounts.google.com'})
"""The `iss` values a Google ID token may carry."""

GOOGLE_ALGORITHM: Final = 'RS256'
"""The algorithm Google signs ID tokens with, and the only one accepted for them."""

GOOGLE_LEEWAY: Final = dt.timedelta(seconds=10)
"""The clock skew allowed when checking a Google ID token's `exp` and `iat`."""

GOOGLE_JWKS: Final = jwt.PyJWKClient(GOOGLE_JWKS_URI, cache_keys=True, lifespan=GOOGLE_JWKS_LIFESPAN)
"""Google's signing keys, fetched on first use and cached for the life of the process (spec §8)."""

session_cookie = APIKeyCookie(
    name=SESSION_COOKIE,
    scheme_name='session',
    description='The `budge_session` cookie that `POST /api/auth/session` sets after a Google sign-in.',
    auto_error=False,
)
"""Reads the session cookie, and declares it as the API's security scheme in the OpenAPI document."""


class GoogleClaims(BaseModel):
    """The claims budge uses from a verified Google ID token; the rest are ignored."""

    model_config = ConfigDict(extra='ignore', frozen=True, strict=True, use_attribute_docstrings=True)

    sub: str
    """The Google account's stable ID, which the allowlist names."""


class SessionClaims(BaseModel):
    """The claims of a `budge_session` token."""

    model_config = ConfigDict(extra='forbid', frozen=True, strict=True, use_attribute_docstrings=True)

    sub: str
    """The signed-in Google account's `sub`."""

    iat: int
    """When the session was issued, in seconds since the epoch."""

    exp: int
    """When the session expires, in seconds since the epoch."""


def unauthenticated(message: str) -> APIError:
    """Return a `401 unauthenticated` error; the SPA shows sign-in.

    >>> unauthenticated('no session').status_code
    401
    """
    return APIError(HTTPStatus.UNAUTHORIZED, 'unauthenticated', message, headers={'WWW-Authenticate': 'APIKey'})


def not_allowlisted() -> APIError:
    """Return a `403 not_allowlisted` error; the SPA shows "not authorized".

    >>> not_allowlisted().code
    'not_allowlisted'
    """
    return APIError(HTTPStatus.FORBIDDEN, 'not_allowlisted', 'This Google account is not allowed to use budge.')


def verify_google_credential(credential: str, *, client_id: str, jwks: jwt.PyJWKClient) -> GoogleClaims:
    """Verify a Google ID token and return its claims.

    The signature must verify (RS256) against the `jwks` key named by the token's `kid`. The token must carry
    `iss` in `GOOGLE_ISSUERS`, `aud` equal to `client_id`, and an `exp` that hasn't passed (with `GOOGLE_LEEWAY`).

    Args:
        credential: The ID token from Google Identity Services.
        client_id: The Google OAuth client ID the token must be issued to.
        jwks: Google's signing keys.

    Returns:
        The token's claims.

    Raises:
        APIError: `401 unauthenticated`, for any token that fails these checks.
        jwt.PyJWKClientConnectionError: Google's key set couldn't be fetched; an `500 internal_error`.

    >>> verify_google_credential('not-a-jwt', client_id='id', jwks=GOOGLE_JWKS)
    Traceback (most recent call last):
    ...
    budge.api.errors.APIError: 401: The Google credential is invalid or expired.
    """
    try:
        key = jwks.get_signing_key_from_jwt(credential)
        claims = jwt.decode(
            credential,
            key,
            algorithms=[GOOGLE_ALGORITHM],
            audience=client_id,
            issuer=GOOGLE_ISSUERS,
            leeway=GOOGLE_LEEWAY,
            options={'require': ['iss', 'aud', 'sub', 'iat', 'exp']},
        )
        return GoogleClaims.model_validate(claims)
    except jwt.PyJWKClientConnectionError:
        raise
    except (jwt.PyJWTError, ValidationError) as error:
        raise unauthenticated('The Google credential is invalid or expired.') from error


def issue_session_token(sub: str, *, key: str, lifetime: dt.timedelta, now: dt.datetime | None = None) -> str:
    """Sign a session token for `sub`, valid for `lifetime` from `now`.

    Args:
        sub: The signed-in Google account's `sub`.
        key: The session-signing key.
        lifetime: How long the session lasts: `REMEMBER_ME_LIFETIME` or `BROWSER_SESSION_LIFETIME`.
        now: The time of issue; defaults to the current time.

    Returns:
        The encoded JWT.

    >>> key = 'k' * 32
    >>> token = issue_session_token('1234', key=key, lifetime=BROWSER_SESSION_LIFETIME)
    >>> claims = read_session_token(token, key=key)
    >>> claims.sub, claims.exp - claims.iat
    ('1234', 43200)
    """
    issued = int((now or dt.datetime.now(dt.UTC)).timestamp())
    payload = {'sub': sub, 'iat': issued, 'exp': issued + int(lifetime.total_seconds())}
    return jwt.encode(payload, key, algorithm=SESSION_ALGORITHM)


def read_session_token(token: str, *, key: str) -> SessionClaims:
    """Verify a session token's signature and `exp`, and return its claims.

    Args:
        token: The `budge_session` cookie's value.
        key: The session-signing key.

    Returns:
        The token's claims.

    Raises:
        APIError: `401 unauthenticated`, for a malformed, tampered or expired token.

    >>> read_session_token('tampered', key='k' * 32)
    Traceback (most recent call last):
    ...
    budge.api.errors.APIError: 401: The session is invalid or expired.
    """
    try:
        claims = jwt.decode(
            token,
            key,
            algorithms=[SESSION_ALGORITHM],
            options={'require': ['sub', 'iat', 'exp'], 'enforce_minimum_key_length': True},
        )
        return SessionClaims.model_validate(claims)
    except (jwt.PyJWTError, ValidationError) as error:
        raise unauthenticated('The session is invalid or expired.') from error


def get_google_jwks() -> jwt.PyJWKClient:
    """Return `GOOGLE_JWKS`. A dependency, so tests can substitute a key set of their own."""
    return GOOGLE_JWKS


def get_session_key(store: Annotated[SecretStore, Depends(get_secret_store)]) -> str:
    """Return the session-signing key from the secret store. A dependency of sign-in and `require_session`."""
    return store.get_session_signing_key()


def require_session(
    token: Annotated[str | None, Security(session_cookie)],
    settings: Annotated[AuthSettings, Depends(get_auth_settings)],
    key: Annotated[str, Depends(get_session_key)],
) -> SessionClaims:
    """Require a valid session whose `sub` is still allowlisted, and return its claims.

    `budge.api.routes.protected_router` declares it as a dependency of every route on it, so every API route requires
    a session except the few on `budge.api.routes.open_router`. It is a named function so tests can replace it through
    `app.dependency_overrides[require_session]`.

    Args:
        token: The `budge_session` cookie, if the request has one.
        settings: The allowlist.
        key: The session-signing key.

    Returns:
        The session's claims.

    Raises:
        APIError: `401 unauthenticated` for a missing, malformed, tampered or expired cookie; `403 not_allowlisted`
            once the session's `sub` is no longer on the allowlist.

    >>> settings = AuthSettings(google_client_id='id', allowed_subs=frozenset({'1234'}))
    >>> key = 'k' * 32
    >>> token = issue_session_token('1234', key=key, lifetime=BROWSER_SESSION_LIFETIME)
    >>> require_session(token, settings, key).sub
    '1234'
    >>> require_session(None, settings, key)
    Traceback (most recent call last):
    ...
    budge.api.errors.APIError: 401: Sign in to continue.
    """
    if token is None:
        raise unauthenticated('Sign in to continue.')
    claims = read_session_token(token, key=key)
    if claims.sub not in settings.allowed_subs:
        raise not_allowlisted()
    return claims
