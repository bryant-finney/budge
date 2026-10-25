"""The OpenAPI document and Swagger UI, served by the app's own routes rather than FastAPI's built-in ones (spec §8).

The routes are the built-in ones rebuilt on an `APIRouter` so that one hook, `DOCS_DEPENDENCIES`, applies a dependency
to all three of them. The docs are exposed in every environment; the auth PR gates them by adding the `budge_session`
cookie + allowlist dependency to `DOCS_DEPENDENCIES` (spec §8: every route except `POST /auth/session` and
`GET /health` requires a valid session). `create_app` includes this router under `/api` with that hook, and none of the
routes appear in the OpenAPI document itself.
"""

from collections.abc import Sequence

from fastapi import APIRouter, FastAPI, Request
from fastapi.openapi.docs import get_swagger_ui_html, get_swagger_ui_oauth2_redirect_html
from fastapi.params import Depends
from fastapi.responses import HTMLResponse, JSONResponse

__all__ = [
    'DOCS_DEPENDENCIES',
    'DOCS_PATH',
    'OAUTH2_REDIRECT_PATH',
    'OPENAPI_PATH',
    'get_openapi_document',
    'get_swagger_ui',
    'get_swagger_ui_oauth2_redirect',
    'router',
]

OPENAPI_PATH = '/openapi.json'
"""The OpenAPI document's path, relative to the `/api` prefix."""

DOCS_PATH = '/docs'
"""Swagger UI's path, relative to the `/api` prefix."""

OAUTH2_REDIRECT_PATH = '/docs/oauth2-redirect'
"""Swagger UI's OAuth2 redirect page's path, relative to the `/api` prefix."""

DOCS_DEPENDENCIES: Sequence[Depends] = ()
"""The auth hook: dependencies every docs route requires, applied by `create_app` when it includes `router`.

Empty until the auth PR adds the `budge_session` session dependency here (spec §8), so for now the docs are public.
`GET /api/health` is on a different router and never picks these up.
"""

router = APIRouter(include_in_schema=False)
"""The docs routes, which `create_app` includes under the `/api` prefix with `DOCS_DEPENDENCIES`."""


def _root_path(request: Request) -> str:
    """Return the ASGI `root_path` the app is mounted under, without a trailing slash (empty when not mounted)."""
    root_path: str = request.scope.get('root_path', '')
    return root_path.rstrip('/')


@router.get(OPENAPI_PATH)
async def get_openapi_document(request: Request) -> JSONResponse:
    """Return the app's OpenAPI document, as FastAPI's built-in `openapi_url` route does.

    Under a non-empty ASGI `root_path`, that path is listed first in `servers`, as in FastAPI's built-in route.

    >>> import asyncio, json
    >>> from starlette.requests import Request
    >>> from budge.api.app import create_app
    >>> response = asyncio.run(get_openapi_document(Request({'type': 'http', 'app': create_app()})))
    >>> sorted(json.loads(response.body)['paths'])
    ['/api/health']
    """
    app: FastAPI = request.app
    schema = app.openapi()
    root_path = _root_path(request)
    if root_path and app.root_path_in_servers:
        servers: list[dict[str, object]] = schema.get('servers', [])
        if root_path not in {server.get('url') for server in servers}:
            schema = {**schema, 'servers': [{'url': root_path}, *servers]}
    return JSONResponse(schema)


@router.get(DOCS_PATH, response_class=HTMLResponse)
async def get_swagger_ui(request: Request) -> HTMLResponse:
    """Return Swagger UI, loading the OpenAPI document from `get_openapi_document`.

    >>> import asyncio
    >>> from starlette.requests import Request
    >>> from budge.api.app import create_app
    >>> response = asyncio.run(get_swagger_ui(Request({'type': 'http', 'app': create_app()})))
    >>> '/api/openapi.json' in response.body.decode()
    True
    """
    app: FastAPI = request.app
    root_path = _root_path(request)
    return get_swagger_ui_html(
        openapi_url=root_path + app.url_path_for(get_openapi_document.__name__),
        title=f'{app.title} - Swagger UI',
        oauth2_redirect_url=root_path + app.url_path_for(get_swagger_ui_oauth2_redirect.__name__),
        init_oauth=app.swagger_ui_init_oauth,
        swagger_ui_parameters=app.swagger_ui_parameters,
    )


@router.get(OAUTH2_REDIRECT_PATH, response_class=HTMLResponse)
async def get_swagger_ui_oauth2_redirect() -> HTMLResponse:
    """Return Swagger UI's OAuth2 redirect page.

    >>> import asyncio
    >>> asyncio.run(get_swagger_ui_oauth2_redirect()).media_type
    'text/html'
    """
    return get_swagger_ui_oauth2_redirect_html()
