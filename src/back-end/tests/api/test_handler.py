"""Tests for the Mangum API Lambda handler, driven with API Gateway HTTP API payload 2.0 events (spec §12).

Local development bypasses API Gateway, so these tests cover the event translation that only runs on AWS.
"""

import copy
import json
from http import HTTPStatus

import pytest
from fastapi import Request
from mangum import Mangum
from mangum.types import LambdaContext

from budge.api.app import create_app
from budge.api.auth import SESSION_COOKIE
from budge.api.handler import handler
from tests.auth import configure, google_credential, session_token

pytestmark = pytest.mark.usefixtures('current_event_loop')


def test_handler_serves_health(apigw_v2_get_health: dict[str, object], lambda_context: LambdaContext) -> None:
    """`budge.api.handler.handler` answers the recorded event with `200 {"ok": true}` as JSON."""
    response = handler(apigw_v2_get_health, lambda_context)

    assert response['statusCode'] == HTTPStatus.OK
    assert response['headers']['content-type'] == 'application/json'
    assert response['isBase64Encoded'] is False
    assert json.loads(response['body']) == {'ok': True}


def _with_path(event: dict[str, object], path: str) -> dict[str, object]:
    """Copy a recorded payload 2.0 `event`, re-addressed to `path`."""
    event = copy.deepcopy(event)
    event['rawPath'] = path
    request_context = event['requestContext']
    assert isinstance(request_context, dict)
    request_context['http']['path'] = path
    return event


async def _echo(request: Request) -> dict[str, object]:
    return {
        'path': request.url.path,
        'probe': request.query_params.getlist('probe'),
        'cookies': dict(request.cookies),
    }


def test_handler_translates_path_query_and_cookies(
    apigw_v2_get_health: dict[str, object], lambda_context: LambdaContext
) -> None:
    """Mangum keeps the `/api` path, the repeated query values, and the `cookies` array (spec §12 "Gap")."""
    app = create_app()
    app.add_api_route('/api/echo', _echo)
    event = _with_path(apigw_v2_get_health, '/api/echo')

    response = Mangum(app, lifespan='off')(event, lambda_context)

    assert response['statusCode'] == HTTPStatus.OK
    assert json.loads(response['body']) == {
        'path': '/api/echo',
        'probe': ['deploy', 'smoke'],
        'cookies': {'budge_session': 's3ss10n.t0k3n', 'theme': 'dark'},
    }


async def _echo_client(request: Request) -> dict[str, object]:
    return {
        'client_host': request.client.host if request.client else None,
        'viewer_address': request.headers.get('cloudfront-viewer-address'),
        'user_agent': request.headers.get('user-agent'),
    }


def test_handler_client_is_the_cloudfront_edge(
    apigw_v2_get_health: dict[str, object], lambda_context: LambdaContext
) -> None:
    """Behind CloudFront, `request.client` is the edge; the viewer's address is only in `cloudfront-viewer-address`.

    Anything that needs the viewer's IP (logging a rejected sign-in, rate limiting) must read that header.
    """
    app = create_app()
    app.add_api_route('/api/echo', _echo_client)
    event = _with_path(apigw_v2_get_health, '/api/echo')

    response = Mangum(app, lifespan='off')(event, lambda_context)

    assert response['statusCode'] == HTTPStatus.OK
    assert json.loads(response['body']) == {
        'client_host': '203.0.113.24',
        'viewer_address': '198.51.100.7:52814',
        'user_agent': 'curl/8.7.1',
    }


def test_handler_sets_the_session_cookie(apigw_v2_get_health: dict[str, object], lambda_context: LambdaContext) -> None:
    """Sign-in through API Gateway: the JSON body goes in, and the cookie comes out in payload 2.0's `cookies` array."""
    event = _with_path(apigw_v2_get_health, '/api/auth/session')
    request_context = event['requestContext']
    headers = event['headers']
    assert isinstance(request_context, dict)
    assert isinstance(headers, dict)
    request_context['http']['method'] = 'POST'
    headers['content-type'] = 'application/json'
    event['body'] = json.dumps({'credential': google_credential(), 'remember_me': True})
    event['rawQueryString'] = ''
    event['cookies'] = []

    response = Mangum(configure(create_app()), lifespan='off')(event, lambda_context)

    assert response['statusCode'] == HTTPStatus.NO_CONTENT
    [cookie] = response['cookies']
    assert cookie.startswith(f'{SESSION_COOKIE}=')
    assert 'Max-Age=2592000' in cookie
    assert 'HttpOnly' in cookie
    assert 'Path=/api' in cookie
    assert 'SameSite=strict' in cookie
    assert 'Secure' in cookie


@pytest.mark.parametrize(
    ('cookies', 'status'),
    [([], HTTPStatus.UNAUTHORIZED), ([f'{SESSION_COOKIE}=garbage'], HTTPStatus.UNAUTHORIZED), (None, HTTPStatus.OK)],
)
def test_handler_reads_the_session_cookie(
    apigw_v2_get_health: dict[str, object], lambda_context: LambdaContext, cookies: list[str] | None, status: int
) -> None:
    """The session check reads `budge_session` from payload 2.0's `cookies` array (`None`: a valid session)."""
    event = _with_path(apigw_v2_get_health, '/api/openapi.json')
    event['cookies'] = [f'{SESSION_COOKIE}={session_token()}', 'theme=dark'] if cookies is None else cookies

    response = Mangum(configure(create_app()), lifespan='off')(event, lambda_context)

    assert response['statusCode'] == status
