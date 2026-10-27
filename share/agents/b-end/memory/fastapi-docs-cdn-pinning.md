---
name: fastapi-docs-cdn-pinning
description: Swagger UI / ReDoc assets in budge.api.routes.docs are pinned to exact jsdelivr releases; how to bump them, the data:, favicon, and why SRI isn't wired
metadata:
  type: project
---

# FastAPI docs pages: pinned CDN assets

`budge.api.routes.docs` passes exact-version `cdn.jsdelivr.net` URLs (`swagger-ui-dist@5.x.y`, `redoc@2.x.y`) to
`get_swagger_ui_html` / `get_redoc_html`, plus `FAVICON_URL = 'data:,'` and `with_google_fonts=False`.

**Why:** reviewer on PR #26 (2026-10-27, thread 4389729511). The pages run on the app's origin, so once sessions land
(#29) a third-party script can `fetch('/api/...')` with the user's `HttpOnly` cookie. FastAPI's defaults float on
`@5`/`@2` and add `fastapi.tiangolo.com` (favicon) and `fonts.googleapis.com` (ReDoc) requests.

**How to apply:**

- To bump, read the npm registry's `time` map (`curl -s https://registry.npmjs.org/<pkg>`) and pick the newest release
  that is at least ~2 weeks old. Then `curl -sI` each jsdelivr file for a 200. On 2026-10-27 that gave `swagger-ui-dist`
  5.33.2 (5.33.3 and 5.34.0 were too new) and `redoc` 2.5.4.
- `redoc`'s `latest` tag is 3.x (3.0.1, 2026-10-14). The reviewer asked for 2.x, and FastAPI's template targets
  ReDoc 2. Moving to 3 is its own change.
- Favicon: use `'data:,'`, not `''`. An empty `href` resolves to the page's own URL, so the browser would request the
  session-gated page again as an icon.
- SRI isn't possible through the helpers. They interpolate the URL straight into `src="..."`/`href="..."`, and there
  is no `integrity`/`crossorigin` parameter. SRI needs our own template or self-hosted assets.
- `tests/api/test_docs.py::test_docs_pages_load_only_exact_cdn_releases` fails on any remote URL in a docs page that is
  not an exact `@M.m.p` jsdelivr asset, so a version bump doesn't need test edits.

Related: [[starlette-testclient-httpx2]].
