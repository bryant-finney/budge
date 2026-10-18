"""The FastAPI application (spec §4, §8).

`app` is the ASGI app that the API Lambda serves through Mangum (`budge.api.handler.handler`) and that local
development runs under uvicorn as `budge.api.app:app` (milestone 2).
"""

from fastapi import FastAPI

import budge
from budge.api.routes import API_PREFIX, api_router

__all__ = ['app', 'create_app']


def create_app() -> FastAPI:
    """Build the API application.

    The OpenAPI document and the interactive docs (including Swagger UI's OAuth2 redirect page) are served under the
    `/api` prefix too: CloudFront routes only `/api/*` to the API, so FastAPI's default `/openapi.json` would be
    unreachable once deployed.

    Returns:
        A new FastAPI application with every route under `/api`.

    >>> sorted(create_app().openapi()['paths'])
    ['/api/health']
    """
    app = FastAPI(
        title='budge',
        version=budge.__version__,
        openapi_url=f'{API_PREFIX}/openapi.json',
        docs_url=f'{API_PREFIX}/docs',
        swagger_ui_oauth2_redirect_url=f'{API_PREFIX}/docs/oauth2-redirect',
        redoc_url=None,
    )
    app.include_router(api_router)
    return app


app = create_app()
"""The module-level ASGI application."""
