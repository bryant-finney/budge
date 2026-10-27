---
name: fastapi-app-settings
description: Why budge's FastAPI app sets redirect_slashes=False (Host-derived 307 leaves the CloudFront origin) and generate_unique_id_function=operation_id (operationId = function name)
metadata:
  type: reference
---

# FastAPI app settings in `budge.api.app.create_app`

- **`redirect_slashes=False`** (PR #26 review, 2026-10-27). Starlette's default answers `/api/health/` with a `307`
  whose `Location` it builds from the request's `Host` header. Behind CloudFront (spec §4, `AllViewerExceptHostHeader`)
  that host is the `execute-api` domain, so the SPA's `fetch` follows it cross-origin and fails opaquely, and a typed
  `/api/docs/` lands the browser on the raw origin. With it off, a trailing slash is a same-origin `404`.
  `tests/api/test_health.py::test_trailing_slash_is_not_redirected` pins it with `follow_redirects=False` (TestClient
  follows redirects by default, so without it a regression shows up as `200`/`401`, not `307`) and asserts no
  `location` header.
- **`generate_unique_id_function=operation_id`** (`route.name`), so `operationId` is `get_health`, not FastAPI's
  default `get_health_api_health_get`; TS generators (orval, hey-api, openapi-typescript `operations`) name client
  functions after it, so changing it later renames the SPA's whole client. Set on the app, it reaches routes on the
  module-level routers included through `include_router` (FastAPI 0.143). FastAPI warns on duplicate operation IDs and
  `filterwarnings = error` makes that fatal, so two routes can't share a function name.
- Reviewer findings like these can be reproduced end to end by driving `budge.api.handler.handler` with
  `tests/events/apigw-v2-get-health.json` and an edited `rawPath` / `requestContext.http.path`.

Related: [[pydantic-model-notes]], [[starlette-testclient-httpx2]].
