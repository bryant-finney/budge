"""Auth test doubles: a self-signed Google JWKS, Google ID tokens signed with it, and signed-in test clients (spec §12).

Nothing here touches the network: `StaticJWKClient` serves a fixed key set in place of Google's, and `configure`
replaces the app's settings, secret store and key set through `app.dependency_overrides`, on that app alone.
"""

import datetime as dt
from collections.abc import Mapping
from typing import Final

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import FastAPI
from fastapi.testclient import TestClient
from jwt.algorithms import RSAAlgorithm
from typing_extensions import override

from budge.api.auth import BROWSER_SESSION_LIFETIME, SESSION_COOKIE, get_google_jwks, issue_session_token
from budge.api.config import AuthSettings, get_auth_settings, get_secret_store
from tests.fakes import SESSION_SIGNING_KEY, FakeSecretStore

GOOGLE_CLIENT_ID: Final = 'budge-test.apps.googleusercontent.com'
"""The Google OAuth client ID the test settings expect as `aud`."""

ALLOWED_SUB: Final = '100000000000000000001'
"""A Google `sub` on the test allowlist."""

OTHER_SUB: Final = '100000000000000000002'
"""A Google `sub` that is not on the test allowlist."""

GOOGLE_ISSUER: Final = 'https://accounts.google.com'
"""The `iss` Google ID tokens carry by default here."""

KEY_ID: Final = 'test-key-1'
"""The `kid` of `GOOGLE_KEY` in the test key set."""

GOOGLE_KEY: Final = rsa.generate_private_key(public_exponent=65537, key_size=2048)
"""The private key that stands in for Google's: its public half is the test key set's only key."""

ROGUE_KEY: Final = rsa.generate_private_key(public_exponent=65537, key_size=2048)
"""A key not in the test key set: tokens it signs carry `KEY_ID` but fail signature verification."""

SETTINGS: Final = AuthSettings(google_client_id=GOOGLE_CLIENT_ID, allowed_subs=frozenset({ALLOWED_SUB}))
"""The test auth settings: `GOOGLE_CLIENT_ID`, and an allowlist of `ALLOWED_SUB` alone."""

HTTPS_BASE_URL: Final = 'https://testserver'
"""The test clients' base URL: `https`, so the client's cookie jar keeps the `Secure` session cookie it is sent."""


def public_jwk(key: rsa.RSAPrivateKey, kid: str = KEY_ID) -> dict[str, object]:
    """Return the public JWK for `key`, as Google's JWKS lists it."""
    jwk: dict[str, object] = {**RSAAlgorithm.to_jwk(key.public_key(), as_dict=True)}
    return {**jwk, 'kid': kid, 'alg': 'RS256', 'use': 'sig'}


class StaticJWKClient(jwt.PyJWKClient):
    """A `PyJWKClient` serving a fixed key set instead of fetching Google's."""

    jwk_set: dict[str, object]
    """The key set `fetch_data` returns."""

    fetches: int
    """How many times the key set was fetched."""

    def __init__(self, *keys: Mapping[str, object]) -> None:
        """Serve `keys` (default: `GOOGLE_KEY`'s public JWK)."""
        super().__init__('https://jwks.invalid/certs')
        self.jwk_set = {'keys': [dict(key) for key in keys] or [public_jwk(GOOGLE_KEY)]}
        self.fetches = 0

    @override
    def fetch_data(self) -> dict[str, object]:
        """Return the fixed key set, caching it as `PyJWKClient.fetch_data` caches a fetched one."""
        self.fetches += 1
        if self.jwk_set_cache is not None:
            self.jwk_set_cache.put(self.jwk_set)
        return self.jwk_set


class UnreachableJWKClient(jwt.PyJWKClient):
    """A `PyJWKClient` whose key-set fetch fails, as when Google is unreachable."""

    def __init__(self) -> None:
        """Create the client."""
        super().__init__('https://jwks.invalid/certs')

    @override
    def fetch_data(self) -> dict[str, object]:
        """Fail as `PyJWKClient` does on a network error."""
        msg = 'Fail to fetch data from the url, err: "connection refused"'
        raise jwt.PyJWKClientConnectionError(msg)


def google_credential(  # noqa: PLR0913 - one keyword per claim a test varies
    *,
    sub: str = ALLOWED_SUB,
    aud: str = GOOGLE_CLIENT_ID,
    iss: str = GOOGLE_ISSUER,
    expires_in: dt.timedelta = dt.timedelta(hours=1),
    key: rsa.RSAPrivateKey = GOOGLE_KEY,
    kid: str = KEY_ID,
) -> str:
    """Return a Google-style ID token signed with `key`, issued now and expiring after `expires_in`."""
    now = int(dt.datetime.now(dt.UTC).timestamp())
    payload = {
        'iss': iss,
        'azp': aud,
        'aud': aud,
        'sub': sub,
        'email': 'household@example.com',
        'email_verified': True,
        'iat': now,
        'exp': now + int(expires_in.total_seconds()),
    }
    return jwt.encode(payload, key, algorithm='RS256', headers={'kid': kid})


def session_token(
    sub: str = ALLOWED_SUB,
    *,
    lifetime: dt.timedelta = BROWSER_SESSION_LIFETIME,
    now: dt.datetime | None = None,
    key: str = SESSION_SIGNING_KEY,
) -> str:
    """Return a `budge_session` token for `sub`, signed with the fake secret store's key by default."""
    return issue_session_token(sub, key=key, lifetime=lifetime, now=now)


def configure(
    application: FastAPI,
    *,
    settings: AuthSettings = SETTINGS,
    store: FakeSecretStore | None = None,
    jwks: jwt.PyJWKClient | None = None,
) -> FastAPI:
    """Point `application`'s auth dependencies at test doubles, and return it.

    Args:
        application: The app to configure; other apps are unaffected.
        settings: The auth settings (default: `SETTINGS`).
        store: The secret store (default: a new `FakeSecretStore`).
        jwks: Google's key set (default: a new `StaticJWKClient`).

    Returns:
        `application`.
    """
    secret_store = store or FakeSecretStore()
    key_set = jwks or StaticJWKClient()
    application.dependency_overrides[get_auth_settings] = lambda: settings
    application.dependency_overrides[get_secret_store] = lambda: secret_store
    application.dependency_overrides[get_google_jwks] = lambda: key_set
    return application


def client_for(
    application: FastAPI, *, token: str | None = None, root_path: str = '', raise_server_exceptions: bool = True
) -> TestClient:
    """Return an `https` test client for `application`, sending `token` as the session cookie if given.

    With `raise_server_exceptions=False`, an unhandled exception reaches the client as the app's `500` response.
    """
    cookies = {SESSION_COOKIE: token} if token is not None else None
    return TestClient(
        application,
        base_url=HTTPS_BASE_URL,
        root_path=root_path,
        cookies=cookies,
        raise_server_exceptions=raise_server_exceptions,
    )
