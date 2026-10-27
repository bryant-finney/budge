"""Session authentication, as a FastAPI dependency rather than middleware (spec §8).

`budge.api.routes.protected_router` declares `require_session` as a dependency of every route on it, so every API route
requires a session except the few on `budge.api.routes.open_router`.
"""

__all__ = ['require_session']


async def require_session() -> None:
    """Require a valid session; a no-op for now, so every request is admitted.

    The auth PR (#29, spec §8) fills this in: it verifies the `budge_session` cookie's signature and `exp`, then
    re-checks its `sub` against the allowlist, answering `401 unauthenticated` or `403 not_allowlisted` on failure. It
    is a named function so that tests can replace it through `app.dependency_overrides[require_session]`.

    Until then this stub fails open, so `tests/api/test_routes.py::test_only_docs_are_protected_until_auth` pins the
    routes behind it to the docs alone: a feature route merged before #29 fails that test. #29 deletes it.

    >>> import asyncio
    >>> asyncio.run(require_session()) is None
    True
    """
