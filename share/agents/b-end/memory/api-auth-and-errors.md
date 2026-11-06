---
name: api-auth-and-errors
description: How #29 built Google sign-in, budge_session, the error envelope and the CSRF check; PyJWT quirks (PyJWKClient fetch_data/cache, HMAC key length); pre-M2 500 from the stub secret store
metadata:
  type: project
---

# API auth, error envelope and CSRF (#29, 2026-10-27)

Decisions and where they live (branch `feat/29/google-sign-in`):

- **Library: `pyjwt[crypto]`.** One typed library verifies Google's RS256 ID tokens and signs/verifies the HS256
  session. `budge.api.auth.GOOGLE_JWKS` is a module-level `PyJWKClient(cache_keys=True, lifespan=3600)`, which is
  spec §8's per-execution-environment JWKS cache. An unknown `kid` triggers PyJWKClient's own refetch.
- **The signing key is a `SecretStore` method** (`get_session_signing_key() -> str`). `SecretsManagerSecretStore` still
  raises `NotImplementedError`, so before M2 implements it, any request that carries a cookie, and every sign-in, is
  `500 internal_error` outside tests. `require_session` takes the store, not the key, and checks for a missing
  cookie first, so a request with no cookie stays `401` whatever the store does.
- **Settings:** `budge.api.config` reads `BUDGE_GOOGLE_CLIENT_ID` and `BUDGE_ALLOWED_GOOGLE_SUBS` (comma-separated).
  `get_auth_settings` and `get_secret_store` are `functools.cache`d dependencies, and tests override them per app
  through `tests.auth.configure`.
- **Error envelope:** `budge.api.errors.install_error_handlers` covers Starlette's `HTTPException`, validation errors and
  `Exception`. `APIError(status, code, message)` picks a code; otherwise the status decides (other 4xx are
  `invalid_request`, 5xx are `internal_error`). The CSRF content-type check answers **415 with `invalid_request`**,
  because §8 has no code for 415.
- **CSRF** is a dependency on *both* routers (`require_json_for_mutations`), so new mutating routes get it
  automatically. FastAPI parses a body with no `Content-Type` as JSON, so the check can't be left implicit.

PyJWT gotchas:

- Overriding `PyJWKClient.fetch_data` (a test stub) skips the `jwk_set_cache.put` that the real one does inside
  `fetch_data`. Mirror it in the stub (`tests.auth.StaticJWKClient`), or caching tests fetch every time.
- `jwt.encode` with an HMAC key shorter than 32 bytes emits `InsecureKeyLengthWarning`, which `filterwarnings = error`
  makes fatal, at collection time when it runs in a `parametrize` list. Test keys must be at least 32 bytes.
  `read_session_token` sets `enforce_minimum_key_length` so a short production key fails loudly.
- `jwt.decode(issuer=...)` takes a container (both Google issuers), and `key=` accepts the `PyJWK` directly.
- Starlette's `add_exception_handler` is typed `(Request, Exception)`. Register narrower handlers through
  `app.exception_handler(Exc)(handler)`, whose decorator type accepts them, instead of `assert isinstance`.

Related: [[route-gating-tests]], [[starlette-testclient-httpx2]], [[fastapi-app-settings]].
