---
name: starlette-testclient-httpx2
description: Starlette 1.8's TestClient needs httpx2; route listing via iter_route_contexts; overrides per app; https base_url for Secure cookies, constructor-only raise_server_exceptions, jar cookies at path /
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

## Cookies and server errors (learned on #29, 2026-10-27)

- The session cookie is `Secure`, so the jar drops it over `http://testserver`. `tests.auth.client_for` uses
  `base_url='https://testserver'`.
- Cookies passed as `TestClient(cookies=...)` sit in the jar at path `/`. A server `Set-Cookie: ...; Path=/api; Max-Age=0` is a different cookie, so it can't clear them. A sign-out test must sign in through the app first, so the
  server sets the cookie it later clears.
- `raise_server_exceptions` only takes effect in the constructor; setting the attribute on a built client does nothing.
  Pass `raise_server_exceptions=False` to see the app's `500` envelope instead of the raised exception.
- Per-request `cookies=` is deprecated in httpx (a fatal warning here). Set cookies on the client or the jar.

Related: [[mangum-event-loop]].
