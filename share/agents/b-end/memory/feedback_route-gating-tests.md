---
name: route-gating-tests
description: Pin public/protected route sets as (method, path) pairs; test the session gate by a denial marker; real-gate and CSRF walks over every route (tripwire removed in #29)
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
- **A fail-open stub ships with a tripwire.** While `require_session` admitted everything,
  `test_only_docs_are_protected_until_auth` pinned the protected set to the four docs routes. #29 (PR on
  `feat/29/google-sign-in`) made `require_session` real and removed the tripwire. The open pin is now
  `{GET /api/health, POST /api/auth/session}`, and `test_real_session_check_gates_every_route_but_the_open_ones` walks
  every route with no cookie and expects `401 unauthenticated` off the open router.
- **Every mutating operation is walked for the CSRF check too:** `tests/api/test_csrf.py` derives the list from the
  route walk, so a new `POST`/`DELETE` route is covered with no test edit.

**Why:** the reviewer showed the path-only pin and the self-derived `== 200` walk both let a public sign-out route
through, and the no-op stub silently exposes anything put on `protected_router`.

**How to apply:** any test that enumerates routes for auth (here or in #29 and later), and any placeholder dependency
that fails open. Related: [[starlette-testclient-httpx2]].
