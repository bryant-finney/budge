"""The `SecretStore` protocol: each connection's Plaid `access_token`, kept apart from the repository (spec §6).

Keeping tokens behind their own interface means nothing in the transaction path can touch token material.
Implementations: the Secrets Manager store in `budge.aws` (milestone 2), and an in-memory fake in the test suite.
"""

from typing import Protocol

__all__ = ['SecretStore']


class SecretStore(Protocol):
    """Per-connection Plaid `access_token` storage, keyed by `connection_id` (spec §6)."""

    def get_access_token(self, connection_id: str) -> str | None:
        """Return the connection's access token, or `None` if no secret exists.

        `None` lets teardown skip `/item/remove` once the secret is already gone (§7).
        """
        ...

    def put_access_token(self, connection_id: str, token: str) -> None:
        """Create or replace the connection's access token."""
        ...

    def delete_access_token(self, connection_id: str) -> None:
        """Delete the connection's access token; a missing secret is a no-op, so teardown is idempotent (§7)."""
        ...
