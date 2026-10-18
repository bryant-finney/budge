---
name: starlette-testclient-httpx2
description: Starlette 1.8's TestClient wants httpx2 and warns with httpx, fatal under filterwarnings=error; tests use httpx.ASGITransport
metadata:
  type: reference
---

# Starlette `TestClient` and `httpx2`

- Starlette 1.8 (via FastAPI 0.143) imports `httpx2` in `starlette.testclient` and, if only `httpx` is installed,
  emits `StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated`. Under
  `filterwarnings = ["error"]` that fails conftest import. Its type hints also name `httpx2`, so pyright strict
  reports every `TestClient` call as unknown when `httpx2` isn't installed.
- `httpx2` (pydantic/httpx2, BSD-3) is the drop-in. On 2026-10-17 the permission classifier denied
  `uv add --group dev httpx2` in an agent session, so #4 drives the app through
  `httpx.AsyncClient(transport=httpx.ASGITransport(app=...))` with `pytest.mark.anyio` (anyio's plugin ships with
  anyio; `tests/conftest.py` pins `anyio_backend` to asyncio). Swapping `httpx` for `httpx2` needs the maintainer's
  approval.
- FastAPI 0.143 stores included routers in `app.routes` as private `_IncludedRouter` objects (no `.path`). To list
  paths, use `app.openapi()['paths']` and the app's `openapi_url`/`docs_url`/`swagger_ui_oauth2_redirect_url`.
- `docs_url` alone leaves Swagger's OAuth2 redirect at `/docs/oauth2-redirect`, outside `/api`. Set
  `swagger_ui_oauth2_redirect_url` too.

Related: [[mangum-event-loop]].
