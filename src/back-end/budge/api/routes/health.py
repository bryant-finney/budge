"""`GET /api/health`: the unauthenticated liveness check the deploy smoke test calls (spec §8, §12)."""

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict

__all__ = ['HealthResponse', 'get_health', 'router']

router = APIRouter(tags=['health'])
"""Health routes; included under the `/api` prefix by `budge.api.routes.open_router`, so they need no session."""


class HealthResponse(BaseModel):
    """The `GET /api/health` response body."""

    model_config = ConfigDict(extra='forbid', use_attribute_docstrings=True)

    ok: Literal[True]
    """Always `true`: the API is up and serving requests."""


# FastAPI publishes a route function's docstring as the operation's OpenAPI `description` (doctest and all), so pass
# `description=` explicitly. A `\f` in the docstring would truncate it too, but ruff's D301 flags it and its `r"""`
# autofix silently disables the truncation. An empty `description=` falls back to the docstring.
@router.get(
    '/health',
    response_model=HealthResponse,
    description='Report that the API is up. Unauthenticated, so the deploy smoke test can call it.',
)
async def get_health() -> HealthResponse:
    """Report that the API is up. Unauthenticated, so the deploy smoke test can call it.

    >>> import asyncio
    >>> asyncio.run(get_health())
    HealthResponse(ok=True)
    """
    return HealthResponse(ok=True)
