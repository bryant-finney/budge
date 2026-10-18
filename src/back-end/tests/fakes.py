"""In-memory fakes of the boundary protocols, shared by the test suite (spec §12 Testing: "a fake repository").

Each fake is deliberately small and dict-backed. `tests/test_protocols.py` proves under mypy and pyright strict that
each one conforms to its protocol.
"""

import contextlib
import datetime as dt
from collections.abc import Generator, Sequence

from budge.models import BankConnection, PlaidEnv, Transaction
from budge.storage import LeaseHeld


class FakeRepository:
    """A dict-backed `budge.storage.Repository`, scoped to one Plaid environment like the real one.

    It stores deep copies, so mutating a returned model doesn't change what's stored (as with a real store), and
    `lock` raises `LeaseHeld` while the same name is already held.
    """

    plaid_env: PlaidEnv
    connections: dict[str, BankConnection]
    rows: dict[str, list[Transaction]]
    held: set[str]

    def __init__(self, plaid_env: PlaidEnv = 'sandbox') -> None:
        """Create an empty repository.

        Args:
            plaid_env: The environment whose connections this repository sees.
        """
        self.plaid_env = plaid_env
        self.connections = {}
        self.rows = {}
        self.held = set()

    def _visible(self, connection: BankConnection | None) -> BankConnection | None:
        if connection is None or connection.plaid_env != self.plaid_env:
            return None
        return connection.model_copy(deep=True)

    def list_connections(self) -> list[BankConnection]:
        """Return this environment's connections."""
        return [c for c in map(self._visible, self.connections.values()) if c is not None]

    def get_connection(self, connection_id: str) -> BankConnection | None:
        """Return the connection, or `None` if it's missing or belongs to the other environment."""
        return self._visible(self.connections.get(connection_id))

    def save_connection(self, connection: BankConnection) -> None:
        """Store a copy of the connection."""
        self.connections[connection.connection_id] = connection.model_copy(deep=True)

    def delete_connection(self, connection_id: str) -> None:
        """Drop the connection's rows, then its metadata; a missing connection is a no-op."""
        self.rows.pop(connection_id, None)
        self.connections.pop(connection_id, None)

    def get_transaction_rows(self, connection_id: str) -> list[Transaction]:
        """Return copies of the connection's stored rows."""
        return [row.model_copy(deep=True) for row in self.rows.get(connection_id, [])]

    def put_transaction_rows(self, connection_id: str, rows: Sequence[Transaction]) -> None:
        """Replace the connection's stored rows with copies of `rows`."""
        self.rows[connection_id] = [row.model_copy(deep=True) for row in rows]

    def get_transactions(self, start: dt.date, end: dt.date, *, discretionary_only: bool = True) -> list[Transaction]:
        """Return this environment's rows with `start <= effective_date <= end`."""
        return [
            row
            for connection in self.list_connections()
            for row in self.get_transaction_rows(connection.connection_id)
            if start <= row.effective_date <= end and (row.is_discretionary or not discretionary_only)
        ]

    @contextlib.contextmanager
    def _lease(self, name: str) -> Generator[None, None, None]:
        if name in self.held:
            raise LeaseHeld(name)
        self.held.add(name)
        try:
            yield
        finally:
            self.held.discard(name)

    def lock(self, name: str) -> contextlib.AbstractContextManager[None]:
        """Hold `name` for the `with` block; raise `LeaseHeld` if it's already held."""
        return self._lease(name)


class FakeSecretStore:
    """A dict-backed `budge.storage.SecretStore`."""

    tokens: dict[str, str]

    def __init__(self) -> None:
        """Create an empty store."""
        self.tokens = {}

    def get_access_token(self, connection_id: str) -> str | None:
        """Return the stored token, or `None`."""
        return self.tokens.get(connection_id)

    def put_access_token(self, connection_id: str, token: str) -> None:
        """Store the token."""
        self.tokens[connection_id] = token

    def delete_access_token(self, connection_id: str) -> None:
        """Drop the token; a missing one is a no-op."""
        self.tokens.pop(connection_id, None)


class FakeIngestionTrigger:
    """A `budge.ingestion.IngestionTrigger` that records each request instead of starting a run."""

    calls: list[str | None]
    """One entry per `trigger` call: the requested id, or `None` for "all connections"."""

    def __init__(self) -> None:
        """Create a trigger with no recorded calls."""
        self.calls = []

    def trigger(self, connection_id: str | None = None) -> None:
        """Record the request."""
        self.calls.append(connection_id)
