"""The `Repository` protocol: persistence for bank connections and their transactions (spec §6).

Implementations: the S3 repository in `budge.aws` (milestone 2), and an in-memory fake in the test suite.
"""

import contextlib
import datetime as dt
from collections.abc import Sequence
from typing import Protocol

from budge.models import BankConnection, Transaction

__all__ = ['LeaseHeld', 'Repository']


class LeaseHeld(Exception):  # noqa: N818 -- the name is fixed by spec §6
    """Raised by `Repository.lock` when another holder has the named lease and it hasn't expired.

    >>> err = LeaseHeld('connection-item-1')
    >>> err.name
    'connection-item-1'
    >>> str(err)
    "lease 'connection-item-1' is held"
    """

    name: str
    """The name of the lease that couldn't be acquired."""

    def __init__(self, name: str) -> None:
        """Record which lease is held.

        Args:
            name: The lease name passed to `Repository.lock`.
        """
        super().__init__(f'lease {name!r} is held')
        self.name = name


class Repository(Protocol):
    """Persistence for bank connections and their normalized transactions (spec §6).

    **Environment scoping:** an implementation is constructed with the current `plaid_env`.
    `list_connections`, `get_connection`, and `get_transactions` see only connections linked in that environment;
    the other environment's records stay stored but invisible.

    **Leases:** every mutation of a connection's objects happens inside `lock(f'connection-{connection_id}')`, and
    `POST /connections` holds `lock('onboarding')` (§6). The repository does not take those leases itself.
    """

    def list_connections(self) -> list[BankConnection]:
        """Return every connection linked in this repository's `plaid_env`."""
        ...

    def get_connection(self, connection_id: str) -> BankConnection | None:
        """Return the connection, or `None` if it doesn't exist in this repository's `plaid_env`."""
        ...

    def save_connection(self, connection: BankConnection) -> None:
        """Create or replace the connection's metadata (its cursor, status, and recurring ids included)."""
        ...

    def delete_connection(self, connection_id: str) -> None:
        """Delete the connection's transactions, then its metadata last; a missing connection is a no-op.

        Deleting the metadata last keeps the connection listed, so a failed teardown can be retried (§7).
        """
        ...

    def get_transaction_rows(self, connection_id: str) -> list[Transaction]:
        """Return every stored transaction for the connection; `[]` if none are stored."""
        ...

    def put_transaction_rows(self, connection_id: str, rows: Sequence[Transaction]) -> None:
        """Replace the connection's stored transactions with `rows`.

        Every row must belong to the connection: `row.connection_id == connection_id`. An empty `rows` is valid and
        clears the stored transactions, which is why the id is passed rather than read from the rows.

        Args:
            connection_id: The connection whose transactions are replaced.
            rows: The connection's complete set of transactions.

        Raises:
            ValueError: If any row's `connection_id` isn't `connection_id`; nothing is stored.
        """
        ...

    def get_transactions(self, start: dt.date, end: dt.date, *, discretionary_only: bool = True) -> list[Transaction]:
        """Return transactions across all of this environment's connections with `start <= effective_date <= end`.

        Args:
            start: The first day of the window, inclusive.
            end: The last day of the window, inclusive.
            discretionary_only: When true (the default), return only rows whose `is_discretionary` is true.

        Returns:
            The matching transactions, in no particular order.
        """
        ...

    def lock(self, name: str) -> contextlib.AbstractContextManager[None]:
        """Hold the named lease for the duration of a `with` block (spec §6).

        The lease is released when the block exits, including on an exception, and a stale (expired) lease is
        taken over.

        Args:
            name: The lease name, e.g. `'onboarding'` or `f'connection-{connection_id}'`.

        Returns:
            A context manager that holds the lease while the block runs.

        Raises:
            LeaseHeld: On entry, if another holder has the lease and it hasn't expired.
        """
        ...
