"""The HTTP API: a FastAPI application served by the API Lambda through Mangum (spec §4, §8).

All routes live under an `/api` router prefix, so the same paths work behind CloudFront and API Gateway and under
local uvicorn. Every request and response body is a Pydantic model, so the generated OpenAPI document is the complete
API contract. Authentication (session cookie plus allowlist) is a FastAPI dependency, not middleware, and every error
uses the single `{"error": {"code", "message"}}` envelope.

Boundary: the API depends only on the `budge.storage` and `budge.ingestion` protocols, never on `boto3` or token
material directly.
"""
