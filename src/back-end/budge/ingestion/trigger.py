"""The `IngestionTrigger` protocol: how the API starts an ingestion run without waiting for it (spec §6, §7, §8).

The API calls it after `POST /connections` (one connection), from `POST /connections/{id}/sync` (one connection),
and from `POST /sync` (all connections). Implementations: the Lambda async-invoke trigger in `budge.aws`
(milestone 2), and a recording fake in the test suite.
"""

from collections.abc import Sequence
from typing import Protocol

__all__ = ['IngestionTrigger']


class IngestionTrigger(Protocol):
    """Starts an asynchronous ingestion run (spec §7 onboarding step 5, §8 sync routes)."""

    def trigger(self, connection_ids: Sequence[str] | None = None) -> None:
        """Ask for an ingestion run and return once the request is accepted, without waiting for the run.

        A failure to trigger after `POST /connections` is not a link failure: the connection is saved and the next
        scheduled run syncs it (§7).

        Args:
            connection_ids: The connections to sync, or `None` for every connection.
        """
        ...
