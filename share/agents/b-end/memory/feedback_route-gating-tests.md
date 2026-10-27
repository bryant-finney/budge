---
name: route-gating-tests
description: Pin public/protected route sets as (method, path) pairs; test the session gate by a distinctive denial marker; give a fail-open auth stub a tripwire test
metadata:
  type: feedback
---

# Route gating tests

Rules for tests that guard which API routes need a session (from PR #26 review, 2026-10-27):

- **Pin operations, never bare paths.** `OPEN_OPERATIONS == {('GET', '/api/health')}`, not a set of paths. Spec §8
  exempts `POST /auth/session` but not `DELETE /auth/session` (sign-out); a path-only pin lets both go public unnoticed.
- **Assert the gate by a marker, not by `== 200`.** The test override of `require_session` raises a `401` with a
  distinctive `detail` (`tests.fakes.deny_session` raises `SESSION_DENIED`, via conftest's `denied_client`); open routes must never return it, protected
  ones always must. Open routes may legitimately 422/401 for their own reasons (e.g. `POST /api/auth/session` with
  no body), so `== 200` breaks for reasons unrelated to gating. Match with `in response.text` so the check survives the
  error-envelope change.
- **A fail-open stub ships with a tripwire.** While `require_session` admits everything,
  `test_only_docs_are_protected_until_auth` pins the protected set to the four docs routes, so a feature route merged
  before #29 fails loudly. #29 deletes the tripwire.

**Why:** the reviewer showed the path-only pin and the self-derived `== 200` walk both let a public sign-out route
through, and the no-op stub silently exposes anything put on `protected_router`.

**How to apply:** any test that enumerates routes for auth (here or in #29 and later), and any placeholder dependency
that fails open. Related: [[starlette-testclient-httpx2]].
