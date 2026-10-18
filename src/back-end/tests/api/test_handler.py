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
from budge.api.handler import handler

pytestmark = pytest.mark.usefixtures('current_event_loop')


def test_handler_serves_health(apigw_v2_get_health: dict[str, object], lambda_context: LambdaContext) -> None:
    """`budge.api.handler.handler` answers the recorded event with `200 {"ok": true}` as JSON."""
    response = handler(apigw_v2_get_health, lambda_context)

    assert response['statusCode'] == HTTPStatus.OK
    assert response['headers']['content-type'] == 'application/json'
    assert response['isBase64Encoded'] is False
    assert json.loads(response['body']) == {'ok': True}


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
    event = copy.deepcopy(apigw_v2_get_health)
    event['rawPath'] = '/api/echo'
    request_context = event['requestContext']
    assert isinstance(request_context, dict)
    request_context['http']['path'] = '/api/echo'

    response = Mangum(app, lifespan='off')(event, lambda_context)

    assert response['statusCode'] == HTTPStatus.OK
    assert json.loads(response['body']) == {
        'path': '/api/echo',
        'probe': ['deploy', 'smoke'],
        'cookies': {'budge_session': 's3ss10n.t0k3n', 'theme': 'dark'},
    }
