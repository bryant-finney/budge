"""The API Lambda's entrypoint.

**Lambda handler string: `budge.api.handler.handler`.**

API Gateway (HTTP API, payload format 2.0) invokes `handler`, which Mangum translates into an ASGI request for
`budge.api.app.app` and back into a Lambda proxy response (spec §4, §12). `lifespan='off'`: the app has no startup or
shutdown hooks, and skipping the lifespan cycle saves work on every invocation.

So the app's lifespan never runs on Lambda, although it does under uvicorn and the tests' `TestClient`. Per-process
setup (such as the JWKS cache, which spec §8 caches "at Lambda module scope") belongs at module scope, where it runs
once per execution environment, at import. A route that relied on a lifespan hook would pass locally and fail once
deployed; adding one means switching this to `lifespan='auto'` and driving `tests/api/test_handler.py` through it.
"""

from mangum import Mangum

from budge.api.app import app

__all__ = ['handler']

handler = Mangum(app, lifespan='off')
"""The Lambda handler: call it with `(event, context)`."""
