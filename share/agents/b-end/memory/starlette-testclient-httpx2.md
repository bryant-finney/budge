---
name: starlette-testclient-httpx2
description: Starlette 1.8's TestClient needs httpx2 (httpx warns, fatal under filterwarnings=error); budge's dev group uses httpx2 since 2026-10-18; FastAPI route-listing quirks
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
- FastAPI 0.143 stores included routers in `app.routes` as private `_IncludedRouter` objects (no `.path`). To list
  paths, use `app.openapi()['paths']` and the app's `openapi_url`/`docs_url`/`swagger_ui_oauth2_redirect_url`.
- `docs_url` alone leaves Swagger's OAuth2 redirect at `/docs/oauth2-redirect`, outside `/api`. Set
  `swagger_ui_oauth2_redirect_url` too.

Related: [[mangum-event-loop]].
