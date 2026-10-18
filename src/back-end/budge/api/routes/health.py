"""`GET /api/health`: the unauthenticated liveness check the deploy smoke test calls (spec §8, §12)."""

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict

__all__ = ['HealthResponse', 'get_health', 'router']

router = APIRouter(tags=['health'])
"""Health routes; included under the `/api` prefix by `budge.api.routes.api_router`."""


class HealthResponse(BaseModel):
    """The `GET /api/health` response body."""

    model_config = ConfigDict(extra='forbid', use_attribute_docstrings=True)

    ok: Literal[True]
    """Always `true`: the API is up and serving requests."""


@router.get('/health', response_model=HealthResponse)
async def get_health() -> HealthResponse:
    """Report that the API is up. Unauthenticated, so the deploy smoke test can call it.

    >>> import asyncio
    >>> asyncio.run(get_health())
    HealthResponse(ok=True)
    """
    return HealthResponse(ok=True)
