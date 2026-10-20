"""`S3Repository`: the S3-backed `budge.storage.Repository` (spec §6). Skeleton only; implemented in milestone 2.

Layout, leases, and write order are specified in spec §6 (`connections/{id}/metadata.json`,
`connections/{id}/transactions.json.gz`, `locks/*.json` via conditional writes).
"""

import contextlib
import datetime as dt
from collections.abc import Sequence

from typing_extensions import override

from budge.models import BankConnection, PlaidEnv, Transaction
from budge.storage import Repository

__all__ = ['S3Repository']

_MILESTONE_2 = 'S3Repository is implemented in milestone 2'


class S3Repository(Repository):
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

    @override
    def list_connections(self) -> list[BankConnection]:
        raise NotImplementedError(_MILESTONE_2)

    @override
    def get_connection(self, connection_id: str) -> BankConnection | None:
        raise NotImplementedError(_MILESTONE_2)

    @override
    def save_connection(self, connection: BankConnection) -> None:
        raise NotImplementedError(_MILESTONE_2)

    @override
    def delete_connection(self, connection_id: str) -> None:
        raise NotImplementedError(_MILESTONE_2)

    @override
    def get_transaction_rows(self, connection_id: str) -> list[Transaction]:
        raise NotImplementedError(_MILESTONE_2)

    @override
    def put_transaction_rows(self, connection_id: str, rows: Sequence[Transaction]) -> None:
        raise NotImplementedError(_MILESTONE_2)

    @override
    def get_transactions(self, start: dt.date, end: dt.date, *, discretionary_only: bool = True) -> list[Transaction]:
        raise NotImplementedError(_MILESTONE_2)

    @override
    def lock(self, name: str) -> contextlib.AbstractContextManager[None]:
        raise NotImplementedError(_MILESTONE_2)
