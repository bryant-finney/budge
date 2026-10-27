"""The FastAPI application (spec §4, §8).

`app` is the ASGI app that the API Lambda serves through Mangum (`budge.api.handler.handler`) and that local
development runs under uvicorn as `budge.api.app:app` (milestone 2).
"""

from fastapi import FastAPI

import budge
from budge.api.routes import open_router, protected_router

__all__ = ['app', 'create_app']


def create_app() -> FastAPI:
    """Build the API application.

    Every route comes from one of two routers under the `/api` prefix (`budge.api.routes`): `open_router`, the only
    unauthenticated routes, and `protected_router`, whose routes all require `budge.api.auth.require_session`
    (spec §8). Tests replace that dependency per app through `app.dependency_overrides[require_session]`.

    The OpenAPI document, Swagger UI (with its OAuth2 redirect page) and ReDoc are served under the `/api` prefix too:
    CloudFront routes only `/api/*` to the API, so FastAPI's default `/openapi.json` would be unreachable once deployed.
    FastAPI's built-in doc routes are off; `budge.api.routes.docs` serves those four routes on `protected_router`.

    Returns:
        A new FastAPI application with every route under `/api`.

    >>> sorted(create_app().openapi()['paths'])
    ['/api/health']
    """
    app = FastAPI(
        title='budge',
        version=budge.__version__,
        openapi_url=None,
        docs_url=None,
        redoc_url=None,
        swagger_ui_oauth2_redirect_url=None,
    )
    app.include_router(open_router)
    app.include_router(protected_router)
    return app


app = create_app()
"""The module-level ASGI application."""
