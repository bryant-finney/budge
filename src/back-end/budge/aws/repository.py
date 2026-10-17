"""`S3Repository`: the S3-backed `budge.storage.Repository` (spec §6). Skeleton only; implemented in milestone 2.

Layout, leases, and write order are specified in spec §6 (`connections/{id}/metadata.json`,
`connections/{id}/transactions.json.gz`, `locks/*.json` via conditional writes).
"""

import contextlib
import datetime as dt
from collections.abc import Sequence

from budge.models import BankConnection, PlaidEnv, Transaction

__all__ = ['S3Repository']

_MILESTONE_2 = 'S3Repository is implemented in milestone 2'


class S3Repository:
    """The S3 implementation of `budge.storage.Repository`, scoped to one Plaid environment."""

    bucket: str
    """The name of the transaction-store bucket."""

    plaid_env: PlaidEnv
    """The environment this repository reads and writes (spec §6, Environment scoping)."""

    def __init__(self, *, bucket: str, plaid_env: PlaidEnv) -> None:
        """Configure the repository.

        Args:
            bucket: The name of the transaction-store bucket.
            plaid_env: The environment whose connections this repository sees.
        """
        self.bucket = bucket
        self.plaid_env = plaid_env

    def list_connections(self) -> list[BankConnection]:
        """See `budge.storage.Repository.list_connections`."""
        raise NotImplementedError(_MILESTONE_2)

    def get_connection(self, connection_id: str) -> BankConnection | None:
        """See `budge.storage.Repository.get_connection`."""
        raise NotImplementedError(_MILESTONE_2)

    def save_connection(self, connection: BankConnection) -> None:
        """See `budge.storage.Repository.save_connection`."""
        raise NotImplementedError(_MILESTONE_2)

    def delete_connection(self, connection_id: str) -> None:
        """See `budge.storage.Repository.delete_connection`."""
        raise NotImplementedError(_MILESTONE_2)

    def get_transaction_rows(self, connection_id: str) -> list[Transaction]:
        """See `budge.storage.Repository.get_transaction_rows`."""
        raise NotImplementedError(_MILESTONE_2)

    def put_transaction_rows(self, connection_id: str, rows: Sequence[Transaction]) -> None:
        """See `budge.storage.Repository.put_transaction_rows`."""
        raise NotImplementedError(_MILESTONE_2)

    def get_transactions(self, start: dt.date, end: dt.date, *, discretionary_only: bool = True) -> list[Transaction]:
        """See `budge.storage.Repository.get_transactions`."""
        raise NotImplementedError(_MILESTONE_2)

    def lock(self, name: str) -> contextlib.AbstractContextManager[None]:
        """See `budge.storage.Repository.lock`."""
        raise NotImplementedError(_MILESTONE_2)
