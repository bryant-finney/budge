"""The FastAPI application (spec §4, §8).

`app` is the ASGI app that the API Lambda serves through Mangum (`budge.api.handler.handler`) and that local
development runs under uvicorn as `budge.api.app:app` (milestone 2).
"""

from collections.abc import Sequence

from fastapi import FastAPI
from fastapi.params import Depends

import budge
from budge.api.routes import API_PREFIX, api_router, docs

__all__ = ['app', 'create_app']


def create_app(*, docs_dependencies: Sequence[Depends] = docs.DOCS_DEPENDENCIES) -> FastAPI:
    """Build the API application.

    The OpenAPI document and Swagger UI (with its OAuth2 redirect page) are served under the `/api` prefix too:
    CloudFront routes only `/api/*` to the API, so FastAPI's default `/openapi.json` would be unreachable once deployed.
    FastAPI's built-in doc routes are off; `budge.api.routes.docs` serves the same URLs from a router whose
    dependencies are `docs_dependencies`, the hook the auth PR fills (spec §8). `GET /api/health` never gets them.

    Args:
        docs_dependencies: Dependencies every docs route requires. Defaults to the hook,
            `budge.api.routes.docs.DOCS_DEPENDENCIES`.

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
    app.include_router(api_router)
    app.include_router(docs.router, prefix=API_PREFIX, dependencies=docs_dependencies)
    return app


app = create_app()
"""The module-level ASGI application."""
