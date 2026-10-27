"""The FastAPI application (spec §4, §8).

`app` is the ASGI app that the API Lambda serves through Mangum (`budge.api.handler.handler`) and that local
development runs under uvicorn as `budge.api.app:app` (milestone 2).
"""

from fastapi import FastAPI
from fastapi.routing import APIRoute

import budge
from budge.api.errors import install_error_handlers
from budge.api.routes import open_router, protected_router

__all__ = ['app', 'create_app', 'operation_id']


def operation_id(route: APIRoute) -> str:
    """Name a route's OpenAPI `operationId` after its path operation function, e.g. `get_health`.

    FastAPI's default appends the path and method (`get_health_api_health_get`), and TypeScript client generators name
    the SPA's functions after `operationId`, so the short form keeps those names readable. FastAPI warns about duplicate
    operation IDs, which `filterwarnings = error` makes fatal in the tests, so two routes can't share a function name.

    Args:
        route: The route to name.

    Returns:
        The route's name, which defaults to its function's name.

    >>> create_app().openapi()['paths']['/api/health']['get']['operationId']
    'get_health'
    """
    return route.name


def create_app() -> FastAPI:
    """Build the API application.

    Every route comes from one of two routers under the `/api` prefix (`budge.api.routes`): `open_router`, the only
    unauthenticated routes, and `protected_router`, whose routes all require `budge.api.auth.require_session`
    (spec §8). Tests replace that dependency per app through `app.dependency_overrides[require_session]`.

    The OpenAPI document, Swagger UI (with its OAuth2 redirect page) and ReDoc are served under the `/api` prefix too:
    CloudFront routes only `/api/*` to the API, so FastAPI's default `/openapi.json` would be unreachable once deployed.
    FastAPI's built-in doc routes are off; `budge.api.routes.docs` serves those four routes on `protected_router`.

    Paths are exact: a trailing slash is a `404`, not a redirect. Each operation's `operationId` is its function's name
    (`operation_id`). Every error response uses the `{"error": {"code", "message"}}` envelope (`budge.api.errors`).

    Returns:
        A new FastAPI application with every route under `/api`.

    >>> sorted(create_app().openapi()['paths'])
    ['/api/auth/session', '/api/health']
    """
    app = FastAPI(
        title='budge',
        version=budge.__version__,
        openapi_url=None,
        docs_url=None,
        redoc_url=None,
        swagger_ui_oauth2_redirect_url=None,
        generate_unique_id_function=operation_id,
        # Starlette's default answers `/api/health/` with a 307 whose `Location` it builds from the `Host` header, and
        # behind CloudFront (spec §4, `AllViewerExceptHostHeader`) that is the API Gateway domain, so following it would
        # leave the app's origin. A trailing slash gets a plain 404 instead.
        redirect_slashes=False,
    )
    install_error_handlers(app)
    app.include_router(open_router)
    app.include_router(protected_router)
    return app


app = create_app()
"""The module-level ASGI application."""
