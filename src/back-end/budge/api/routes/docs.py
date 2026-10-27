"""The OpenAPI document, Swagger UI and ReDoc, served by the app's own routes rather than FastAPI's built-in ones (§8).

The routes are the built-in ones rebuilt on an `APIRouter`, which `budge.api.routes.protected_router` includes under
`/api`, so all four require a session like every other route but `POST /auth/session` and `GET /health` (spec §8).
`budge.api.auth.require_session` admits every request until the auth PR fills it in, so for now the docs are public.
None of the routes appear in the OpenAPI document itself.

Swagger UI and ReDoc run third-party JavaScript on the app's own origin, where it can call the API with the signed-in
user's session cookie, so both pages load it (and Swagger UI its CSS) from exact `swagger-ui-dist` and `redoc` versions
on `cdn.jsdelivr.net` rather than FastAPI's floating `@5` and `@2` tags: an exact npm version there never changes. The
pages fetch nothing else from a third party: no favicon from `fastapi.tiangolo.com` and no Google Fonts for ReDoc.
"""

from typing import Final

from fastapi import APIRouter, FastAPI, Request
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html, get_swagger_ui_oauth2_redirect_html
from fastapi.responses import HTMLResponse, JSONResponse

__all__ = [
    'FAVICON_URL',
    'REDOC_JS_URL',
    'SWAGGER_UI_CSS_URL',
    'SWAGGER_UI_JS_URL',
    'get_openapi_document',
    'get_redoc',
    'get_swagger_ui',
    'get_swagger_ui_oauth2_redirect',
    'router',
]

SWAGGER_UI_JS_URL: Final = 'https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.33.2/swagger-ui-bundle.js'
"""Swagger UI's JavaScript bundle, pinned to an exact `swagger-ui-dist` release."""

SWAGGER_UI_CSS_URL: Final = 'https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.33.2/swagger-ui.css'
"""Swagger UI's stylesheet, from the same `swagger-ui-dist` release as `SWAGGER_UI_JS_URL`."""

REDOC_JS_URL: Final = 'https://cdn.jsdelivr.net/npm/redoc@2.5.4/bundles/redoc.standalone.js'
"""ReDoc's standalone JavaScript bundle, pinned to an exact `redoc` release."""

FAVICON_URL: Final = 'data:,'
"""Both pages' favicon: an empty `data:` URI, so the browser fetches no icon (an empty `href` would fetch the page)."""

router = APIRouter(include_in_schema=False)
"""The docs routes, which `budge.api.routes.protected_router` includes under the `/api` prefix."""


def _root_path(request: Request) -> str:
    """Return the ASGI `root_path` the app is mounted under, without a trailing slash (empty when not mounted)."""
    root_path: str = request.scope.get('root_path', '')
    return root_path.rstrip('/')


@router.get('/openapi.json')
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


@router.get('/docs', response_class=HTMLResponse)
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
        swagger_js_url=SWAGGER_UI_JS_URL,
        swagger_css_url=SWAGGER_UI_CSS_URL,
        swagger_favicon_url=FAVICON_URL,
        oauth2_redirect_url=root_path + app.url_path_for(get_swagger_ui_oauth2_redirect.__name__),
        init_oauth=app.swagger_ui_init_oauth,
        swagger_ui_parameters=app.swagger_ui_parameters,
    )


@router.get('/docs/oauth2-redirect', response_class=HTMLResponse)
async def get_swagger_ui_oauth2_redirect() -> HTMLResponse:
    """Return Swagger UI's OAuth2 redirect page.

    >>> import asyncio
    >>> asyncio.run(get_swagger_ui_oauth2_redirect()).media_type
    'text/html'
    """
    return get_swagger_ui_oauth2_redirect_html()


@router.get('/redoc', response_class=HTMLResponse)
async def get_redoc(request: Request) -> HTMLResponse:
    """Return ReDoc, loading the OpenAPI document from `get_openapi_document`, as FastAPI's built-in `redoc_url` does.

    >>> import asyncio
    >>> from starlette.requests import Request
    >>> from budge.api.app import create_app
    >>> response = asyncio.run(get_redoc(Request({'type': 'http', 'app': create_app()})))
    >>> '/api/openapi.json' in response.body.decode()
    True
    """
    app: FastAPI = request.app
    return get_redoc_html(
        openapi_url=_root_path(request) + app.url_path_for(get_openapi_document.__name__),
        title=f'{app.title} - ReDoc',
        redoc_js_url=REDOC_JS_URL,
        redoc_favicon_url=FAVICON_URL,
        with_google_fonts=False,
    )
