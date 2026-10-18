"""The API Lambda's entrypoint.

**Lambda handler string: `budge.api.handler.handler`.**

API Gateway (HTTP API, payload format 2.0) invokes `handler`, which Mangum translates into an ASGI request for
`budge.api.app.app` and back into a Lambda proxy response (spec §4, §12). `lifespan='off'`: the app has no startup or
shutdown hooks, and skipping the lifespan cycle saves work on every invocation.
"""

from mangum import Mangum

from budge.api.app import app

__all__ = ['handler']

handler = Mangum(app, lifespan='off')
"""The Lambda handler: call it with `(event, context)`."""
