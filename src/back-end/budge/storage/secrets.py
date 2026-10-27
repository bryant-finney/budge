"""The `SecretStore` protocol: each connection's Plaid `access_token`, kept apart from the repository (spec §6).

Keeping tokens behind their own interface means nothing in the transaction path can touch token material. The store
also holds the API's session-signing key (spec §8), which Pulumi generates into Secrets Manager.
Implementations: the Secrets Manager store in `budge.aws` (milestone 2), and an in-memory fake in the test suite.
"""

from typing import Protocol

__all__ = ['SecretStore']


class SecretStore(Protocol):
    """Per-connection Plaid `access_token` storage, keyed by `connection_id` (spec §6), and the session-signing key."""

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

    def get_session_signing_key(self) -> str:
        """Return the HS256 key that signs and verifies `budge_session` cookies (spec §8).

        Rotating the key signs everyone out. Implementations may cache it for the life of the process.
        """
        ...
