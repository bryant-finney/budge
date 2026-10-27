"""Tests for Google sign-in, the `budge_session` cookie, and the session dependency (spec §8 Auth, §12 Testing).

Google ID tokens are signed with a self-signed key served by `tests.auth.StaticJWKClient`, so nothing touches the
network. The clients use an `https` base URL, so their cookie jar keeps the `Secure` session cookie.
"""

import datetime as dt
import logging
from collections.abc import Iterator
from http import HTTPStatus
from http.cookies import Morsel, SimpleCookie

import httpx2
import jwt
import pytest
from fastapi import status
from fastapi.testclient import TestClient

from budge.api.app import create_app
from budge.api.auth import (
    BROWSER_SESSION_LIFETIME,
    GOOGLE_ISSUERS,
    GOOGLE_JWKS,
    GOOGLE_JWKS_LIFESPAN,
    GOOGLE_JWKS_URI,
    REMEMBER_ME_LIFETIME,
    SESSION_COOKIE,
    get_google_jwks,
    read_session_token,
)
from budge.api.config import AuthSettings
from tests.auth import (
    ALLOWED_SUB,
    GOOGLE_KEY,
    OTHER_SUB,
    ROGUE_KEY,
    SETTINGS,
    StaticJWKClient,
    UnreachableJWKClient,
    client_for,
    configure,
    google_credential,
    public_jwk,
    session_token,
)
from tests.fakes import SESSION_SIGNING_KEY, FakeSecretStore

JSON = {'content-type': 'application/json'}
"""The header every mutating request needs (spec §8 CSRF)."""

SESSION_URL = '/api/auth/session'
"""Sign-in (`POST`) and sign-out (`DELETE`)."""

PROTECTED_URL = '/api/openapi.json'
"""A route that requires a session."""


def sign_in(client: TestClient, credential: str, *, remember_me: bool = False) -> httpx2.Response:
    """Post `credential` to `POST /api/auth/session` as the SPA does."""
    return client.post(SESSION_URL, json={'credential': credential, 'remember_me': remember_me}, headers=JSON)


def set_cookie(response: httpx2.Response) -> Morsel[str]:
    """Parse the response's one `Set-Cookie` header into the `budge_session` morsel."""
    headers = response.headers.get_list('set-cookie')
    assert len(headers) == 1
    cookie: SimpleCookie = SimpleCookie()
    cookie.load(headers[0])
    return cookie[SESSION_COOKIE]


def assert_error(response: httpx2.Response, status_code: int, code: str) -> None:
    """Assert `response` is an error envelope with `status_code` and `code`, and sets no cookie."""
    assert response.status_code == status_code
    assert response.json()['error']['code'] == code
    assert 'set-cookie' not in response.headers


@pytest.fixture
def jwks() -> StaticJWKClient:
    """The self-signed stand-in for Google's key set."""
    return StaticJWKClient()


@pytest.fixture
def anonymous(jwks: StaticJWKClient) -> Iterator[TestClient]:
    """A client with no session, for an app that verifies Google tokens against `jwks`."""
    with client_for(configure(create_app(), jwks=jwks)) as test_client:
        yield test_client


# --- POST /api/auth/session ---------------------------------------------------------------------------------------


def test_sign_in_sets_a_browser_session_cookie(anonymous: TestClient) -> None:
    """Without remember-me: `204`, a cookie with the §8 attributes and no `Max-Age`, and a 12-hour token."""
    response = sign_in(anonymous, google_credential(), remember_me=False)

    assert response.status_code == HTTPStatus.NO_CONTENT
    assert response.content == b''
    morsel = set_cookie(response)
    assert morsel['httponly'] is True
    assert morsel['secure'] is True
    assert morsel['samesite'] == 'strict'
    assert morsel['path'] == '/api'
    assert morsel['max-age'] == ''
    assert morsel['expires'] == ''
    claims = read_session_token(morsel.value, key=SESSION_SIGNING_KEY)
    assert claims.sub == ALLOWED_SUB
    assert claims.exp - claims.iat == BROWSER_SESSION_LIFETIME.total_seconds()


def test_sign_in_with_remember_me_lasts_30_days(anonymous: TestClient) -> None:
    """With remember-me: the cookie's `Max-Age` and the token's lifetime are both 30 days."""
    response = sign_in(anonymous, google_credential(), remember_me=True)

    assert response.status_code == HTTPStatus.NO_CONTENT
    morsel = set_cookie(response)
    assert morsel['max-age'] == str(int(REMEMBER_ME_LIFETIME.total_seconds())) == '2592000'
    claims = read_session_token(morsel.value, key=SESSION_SIGNING_KEY)
    assert claims.exp - claims.iat == REMEMBER_ME_LIFETIME.total_seconds()


def test_sign_in_cookie_opens_protected_routes(anonymous: TestClient) -> None:
    """The cookie sign-in sets is what the session check accepts afterwards."""
    assert anonymous.get(PROTECTED_URL).status_code == HTTPStatus.UNAUTHORIZED

    assert sign_in(anonymous, google_credential()).status_code == HTTPStatus.NO_CONTENT

    assert anonymous.get(PROTECTED_URL).status_code == HTTPStatus.OK


@pytest.mark.parametrize('issuer', sorted(GOOGLE_ISSUERS))
def test_sign_in_accepts_both_google_issuers(anonymous: TestClient, issuer: str) -> None:
    """Google ID tokens carry either issuer form; both are accepted."""
    assert sign_in(anonymous, google_credential(iss=issuer)).status_code == HTTPStatus.NO_CONTENT


def test_sign_in_allows_ten_seconds_of_clock_skew(anonymous: TestClient) -> None:
    """A token that expired 5 s ago is within the ~10 s leeway (spec §8)."""
    credential = google_credential(expires_in=dt.timedelta(seconds=-5))

    assert sign_in(anonymous, credential).status_code == HTTPStatus.NO_CONTENT


@pytest.mark.parametrize(
    'credential',
    [
        pytest.param(google_credential(key=ROGUE_KEY), id='bad-signature'),
        pytest.param(google_credential(iss='https://accounts.example.com'), id='wrong-iss'),
        pytest.param(google_credential(aud='someone-else.apps.googleusercontent.com'), id='wrong-aud'),
        pytest.param(google_credential(expires_in=dt.timedelta(seconds=-60)), id='expired'),
        pytest.param(google_credential(kid='unknown-key'), id='unknown-kid'),
        pytest.param('not.a.jwt', id='malformed'),
        pytest.param(jwt.encode({'sub': ALLOWED_SUB}, SESSION_SIGNING_KEY, algorithm='HS256'), id='hs256-no-kid'),
        pytest.param(
            jwt.encode({'sub': ALLOWED_SUB}, SESSION_SIGNING_KEY, algorithm='HS256', headers={'kid': 'test-key-1'}),
            id='hs256-algorithm-confusion',
        ),
    ],
)
def test_sign_in_rejects_invalid_google_tokens(anonymous: TestClient, credential: str) -> None:
    """A bad signature, wrong `iss` or `aud`, an expired or malformed token: `401 unauthenticated`, no cookie."""
    assert_error(sign_in(anonymous, credential), HTTPStatus.UNAUTHORIZED, 'unauthenticated')


def test_sign_in_rejects_a_token_without_a_string_sub(anonymous: TestClient) -> None:
    """A signature-valid token whose `sub` isn't a string fails the claims model: `401 unauthenticated`."""
    now = int(dt.datetime.now(dt.UTC).timestamp())
    payload = {'iss': 'accounts.google.com', 'aud': SETTINGS.google_client_id, 'sub': 1, 'iat': now, 'exp': now + 60}
    credential = jwt.encode(payload, GOOGLE_KEY, algorithm='RS256', headers={'kid': 'test-key-1'})

    assert_error(sign_in(anonymous, credential), HTTPStatus.UNAUTHORIZED, 'unauthenticated')


def test_sign_in_rejects_and_logs_a_sub_not_on_the_allowlist(
    anonymous: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    """A valid identity that isn't allowlisted: `403 not_allowlisted`, and its `sub` is logged for bootstrap (§8)."""
    with caplog.at_level(logging.WARNING, logger='budge.api.routes.auth'):
        response = sign_in(anonymous, google_credential(sub=OTHER_SUB))

    assert_error(response, HTTPStatus.FORBIDDEN, 'not_allowlisted')
    [record] = caplog.records
    assert vars(record)['sub'] == OTHER_SUB
    assert OTHER_SUB in record.getMessage()


def test_sign_in_fails_closed_when_google_is_unreachable() -> None:
    """If Google's key set can't be fetched, sign-in fails with `500 internal_error`, not a session."""
    application = configure(create_app(), jwks=UnreachableJWKClient())
    with client_for(application, raise_server_exceptions=False) as test_client:
        response = sign_in(test_client, google_credential())

    assert_error(response, HTTPStatus.INTERNAL_SERVER_ERROR, 'internal_error')


@pytest.mark.parametrize(
    'body',
    [
        pytest.param({}, id='empty'),
        pytest.param({'credential': 'x'}, id='no-remember-me'),
        pytest.param({'credential': 'x', 'remember_me': 'yes'}, id='remember-me-not-bool'),
        pytest.param({'credential': 'x', 'remember_me': False, 'extra': 1}, id='unknown-field'),
    ],
)
def test_sign_in_validates_its_body(anonymous: TestClient, body: dict[str, object]) -> None:
    """A malformed body answers `422 invalid_request` in the error envelope, not FastAPI's `{"detail": [...]}`."""
    response = anonymous.post(SESSION_URL, json=body, headers=JSON)

    assert_error(response, status.HTTP_422_UNPROCESSABLE_CONTENT, 'invalid_request')
    assert 'detail' not in response.json()


@pytest.mark.parametrize(
    'headers', [pytest.param({}, id='none'), pytest.param({'content-type': 'text/plain'}, id='text')]
)
def test_sign_in_requires_a_json_content_type(anonymous: TestClient, headers: dict[str, str]) -> None:
    """Sign-in is a mutating route, so it requires `Content-Type: application/json` (spec §8 CSRF)."""
    body = b'{"credential": "x", "remember_me": false}'

    response = anonymous.post(SESSION_URL, content=body, headers=headers)

    assert_error(response, HTTPStatus.UNSUPPORTED_MEDIA_TYPE, 'invalid_request')


def test_google_key_set_is_cached_per_process() -> None:
    """Sign-in reads Google's keys from one module-level client that caches them (spec §8 "cached at module scope")."""
    assert get_google_jwks() is GOOGLE_JWKS
    assert GOOGLE_JWKS.uri == GOOGLE_JWKS_URI
    assert GOOGLE_JWKS.jwk_set_cache is not None
    assert GOOGLE_JWKS.jwk_set_cache.lifespan == GOOGLE_JWKS_LIFESPAN


def test_google_key_set_is_fetched_once_for_many_sign_ins() -> None:
    """With the key set cached, repeated sign-ins don't refetch it."""
    jwks = StaticJWKClient(public_jwk(GOOGLE_KEY))
    with client_for(configure(create_app(), jwks=jwks)) as test_client:
        for _ in range(3):
            assert sign_in(test_client, google_credential()).status_code == HTTPStatus.NO_CONTENT

    assert jwks.fetches == 1


# --- DELETE /api/auth/session -------------------------------------------------------------------------------------


def test_sign_out_clears_the_cookie(anonymous: TestClient) -> None:
    """Sign-out answers `204` and expires the cookie sign-in set, with the attributes it was set with."""
    assert sign_in(anonymous, google_credential()).status_code == HTTPStatus.NO_CONTENT
    assert anonymous.get(PROTECTED_URL).status_code == HTTPStatus.OK

    response = anonymous.delete(SESSION_URL, headers=JSON)

    assert response.status_code == HTTPStatus.NO_CONTENT
    morsel = set_cookie(response)
    assert morsel.value == ''
    assert morsel['max-age'] == '0'
    assert morsel['path'] == '/api'
    assert morsel['secure'] is True
    assert morsel['httponly'] is True
    assert morsel['samesite'] == 'strict'
    assert SESSION_COOKIE not in anonymous.cookies
    assert anonymous.get(PROTECTED_URL).status_code == HTTPStatus.UNAUTHORIZED


def test_sign_out_requires_a_session(anonymous: TestClient) -> None:
    """Sign-out isn't one of §8's open routes, so it needs a session like every other."""
    assert_error(anonymous.delete(SESSION_URL, headers=JSON), HTTPStatus.UNAUTHORIZED, 'unauthenticated')


def test_sign_out_requires_a_json_content_type(client: TestClient) -> None:
    """Sign-out is a mutating route, so it requires `Content-Type: application/json` even with no body."""
    assert_error(client.delete(SESSION_URL), HTTPStatus.UNSUPPORTED_MEDIA_TYPE, 'invalid_request')


# --- the session dependency ---------------------------------------------------------------------------------------


def _tampered(token: str) -> str:
    """Swap the token's payload for one naming `OTHER_SUB`, keeping the original signature."""
    header, _, signature = token.split('.')
    forged = session_token(OTHER_SUB).split('.')[1]
    return f'{header}.{forged}.{signature}'


@pytest.mark.parametrize(
    'token',
    [
        pytest.param('', id='empty'),
        pytest.param('not-a-jwt', id='malformed'),
        pytest.param(_tampered(session_token()), id='tampered'),
        pytest.param(session_token(key='another-signing-key-0123456789abcdef'), id='other-key'),
        pytest.param(
            session_token(now=dt.datetime.now(dt.UTC) - BROWSER_SESSION_LIFETIME - dt.timedelta(seconds=1)),
            id='expired',
        ),
        pytest.param(jwt.encode({'sub': ALLOWED_SUB, 'iat': 0}, SESSION_SIGNING_KEY, algorithm='HS256'), id='no-exp'),
        pytest.param(
            jwt.encode(
                {'sub': ALLOWED_SUB, 'iat': 0, 'exp': 2**40, 'admin': True}, SESSION_SIGNING_KEY, algorithm='HS256'
            ),
            id='unknown-claim',
        ),
    ],
)
def test_session_check_rejects_bad_cookies(token: str) -> None:
    """A missing, malformed, tampered, foreign-key or expired cookie: `401 unauthenticated`."""
    with client_for(configure(create_app()), token=token) as test_client:
        response = test_client.get(PROTECTED_URL)

    assert_error(response, HTTPStatus.UNAUTHORIZED, 'unauthenticated')
    assert response.headers['www-authenticate'] == 'APIKey'


def test_session_check_rejects_no_cookie(anonymous_client: TestClient) -> None:
    """No cookie at all: `401 unauthenticated`, so the SPA shows sign-in."""
    assert_error(anonymous_client.get(PROTECTED_URL), HTTPStatus.UNAUTHORIZED, 'unauthenticated')


def test_session_check_rejects_a_sub_removed_from_the_allowlist() -> None:
    """Removing a `sub` from the allowlist revokes its existing sessions: `403 not_allowlisted` (spec §8)."""
    store = FakeSecretStore()
    token = session_token()
    with client_for(configure(create_app(), store=store), token=token) as test_client:
        assert test_client.get(PROTECTED_URL).status_code == HTTPStatus.OK

    revoked = AuthSettings(google_client_id=SETTINGS.google_client_id, allowed_subs=frozenset())
    with client_for(configure(create_app(), settings=revoked, store=store), token=token) as test_client:
        assert_error(test_client.get(PROTECTED_URL), HTTPStatus.FORBIDDEN, 'not_allowlisted')


def test_rotating_the_signing_key_signs_everyone_out(client: TestClient) -> None:
    """A session signed with the old key fails once the store holds a new one (spec §8)."""
    rotated = FakeSecretStore(session_signing_key='rotated-session-signing-key-0123456789')
    with client_for(configure(create_app(), store=rotated), token=session_token()) as test_client:
        assert_error(test_client.get(PROTECTED_URL), HTTPStatus.UNAUTHORIZED, 'unauthenticated')

    assert client.get(PROTECTED_URL).status_code == HTTPStatus.OK


# --- the OpenAPI contract -----------------------------------------------------------------------------------------


def test_openapi_documents_the_auth_routes_and_errors() -> None:
    """The auth routes, their request and error models, and the cookie scheme are in the contract (spec §13 M2)."""
    document = create_app().openapi()
    sign_in_operation = document['paths'][SESSION_URL]['post']
    sign_out_operation = document['paths'][SESSION_URL]['delete']
    schemas = document['components']['schemas']

    assert sign_in_operation['operationId'] == 'create_session'
    assert sign_in_operation['requestBody']['content']['application/json']['schema'] == {
        '$ref': '#/components/schemas/SessionRequest'
    }
    assert sorted(sign_in_operation['responses']) == ['204', '401', '403', '415', '422']
    assert sign_in_operation['responses']['422']['content']['application/json']['schema'] == {
        '$ref': '#/components/schemas/ErrorResponse'
    }
    assert 'security' not in sign_in_operation
    assert sign_out_operation['operationId'] == 'delete_session'
    assert sorted(sign_out_operation['responses']) == ['204', '401', '403', '415']
    assert sign_out_operation['security'] == [{'session': []}]
    assert document['components']['securitySchemes'] == {
        'session': {
            'type': 'apiKey',
            'in': 'cookie',
            'name': 'budge_session',
            'description': 'The `budge_session` cookie that `POST /api/auth/session` sets after a Google sign-in.',
        }
    }
    assert {'SessionRequest', 'ErrorResponse', 'ErrorDetail'} <= set(schemas)
    assert 'HTTPValidationError' not in schemas
    assert schemas['ErrorDetail']['properties']['code']['enum'] == [
        'unauthenticated',
        'not_allowlisted',
        'not_found',
        'duplicate_account',
        'lease_held',
        'invalid_request',
        'plaid_error',
        'internal_error',
    ]
