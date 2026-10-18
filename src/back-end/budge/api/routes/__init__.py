"""The API's routes, all mounted under one `/api` router (spec §4, §8).

CloudFront forwards `/api/...` paths to API Gateway unchanged, so declaring the prefix in FastAPI itself makes paths
identical on AWS and under local uvicorn, and Mangum needs no base-path setting.
"""

from fastapi import APIRouter

from budge.api.routes import health

__all__ = ['API_PREFIX', 'api_router']

API_PREFIX = '/api'
"""The path prefix every route is served under."""

api_router = APIRouter(prefix=API_PREFIX)
"""The single router the app includes; each feature router is included here."""

api_router.include_router(health.router)
