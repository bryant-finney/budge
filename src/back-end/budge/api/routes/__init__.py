"""The API's routes, split between two routers under one `/api` prefix (spec §4, §8).

CloudFront forwards `/api/...` paths to API Gateway unchanged, so declaring the prefix in FastAPI itself makes paths
identical on AWS and under local uvicorn, and Mangum needs no base-path setting.

Spec §8 requires a session for every request except `POST /auth/session` and `GET /health`. FastAPI router
dependencies accumulate down through included routers and have no per-route opt-out, so the few public routes can't be
excluded from a router that requires a session; they sit on a separate router instead. `create_app` includes both.

Both routers also depend on `budge.api.csrf.require_json_for_mutations`, so every mutating route on either one requires
`Content-Type: application/json` (spec §8 CSRF).
"""

from http import HTTPStatus

from fastapi import APIRouter, Depends

from budge.api.auth import require_session
from budge.api.csrf import require_json_for_mutations
from budge.api.errors import error_responses
from budge.api.routes import auth, docs, health

__all__ = ['API_PREFIX', 'open_router', 'protected_router']

API_PREFIX = '/api'
"""The path prefix every route is served under."""

protected_router = APIRouter(
    prefix=API_PREFIX,
    dependencies=[Depends(require_session), Depends(require_json_for_mutations)],
    responses=error_responses(HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN),
)
"""The router for every API route that requires a session, which is every route not on `open_router`.

Each feature router, the sign-out route, and the docs routes (`budge.api.routes.docs`) are included here, so each route
requires `require_session`, and each operation documents its `401`/`403` error responses.
"""

open_router = APIRouter(prefix=API_PREFIX, dependencies=[Depends(require_json_for_mutations)])
"""The router for the unauthenticated routes: `GET /api/health` and `POST /api/auth/session` (sign-in).

Adding a route here makes it public, so do it deliberately: `tests/api/test_routes.py` pins this router's
`(method, path)` operations, so the change has to show up in a test, too.
"""

protected_router.include_router(auth.router)
protected_router.include_router(docs.router)
open_router.include_router(auth.sign_in_router)
open_router.include_router(health.router)
