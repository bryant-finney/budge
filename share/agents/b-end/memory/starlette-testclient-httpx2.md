---
name: starlette-testclient-httpx2
description: Starlette 1.8's TestClient needs httpx2 (httpx warns, fatal under filterwarnings=error); FastAPI 0.143 route listing via iter_route_contexts; dependency_overrides stay per app
metadata:
  type: reference
---

# Starlette `TestClient` and `httpx2`

- Starlette 1.8 (via FastAPI 0.143) imports `httpx2` in `starlette.testclient`. If only `httpx` is installed, it
  emits `StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated`, which fails conftest
  import under `filterwarnings = ["error"]`. Its type hints also name `httpx2`, so pyright strict sees `TestClient`
  as unknown without it.
- **Resolved 2026-10-18 (PR #26, `61dbe8e`):** the maintainer approved the swap (an earlier agent session's
  `uv add` had been denied by the permission classifier). The dev group has `httpx2~=2.13` (pydantic/httpx2,
  BSD-3-Clause, `py.typed`) in place of `httpx`. `tests/conftest.py`'s `client` fixture is
  `with TestClient(create_app())`, which runs the lifespan, and the API tests are plain sync tests with no anyio
  marker.
- TestClient runs the app on an anyio portal thread, so it doesn't unset the main thread's current loop. See
  [[mangum-event-loop]].
- FastAPI 0.143 stores included routers in `app.routes` as private `_IncludedRouter` objects (no `.path`), and
  resolves them lazily, so a router's routes and `dependencies` are read through live references, not copied. To list
  every route, including `include_in_schema=False` ones, use the public `fastapi.routing.iter_route_contexts(routes)`:
  it flattens included routers and yields `RouteContext`s with typed `.path`/`.methods` (stick to those; its
  `__getattr__` is `Any`). It works on a sub-router's `.routes` too, with the parent prefixes folded in. GET routes
  list only `GET`, no `HEAD`. `tests/api/test_routes.py` uses it for the session-gating walk.
- `app.dependency_overrides` stays per app even though `create_app()` apps share module-level routers: the include
  context carries the including app as `dependency_overrides_provider`.
- `docs_url` alone leaves Swagger's OAuth2 redirect at `/docs/oauth2-redirect`, outside `/api`. Set
  `swagger_ui_oauth2_redirect_url` too.

Related: [[mangum-event-loop]].
