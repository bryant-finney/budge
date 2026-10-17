"""Storage boundary: the `Repository` and `SecretStore` protocols the rest of the app depends on (spec §6).

`Repository` covers bank connections and their normalized transactions, plus the `lock(name)` lease context manager.
It is constructed with the current `plaid_env`, and reads see only that environment's records. `SecretStore` is a
separate interface for each connection's Plaid `access_token`, so nothing in the transaction path can touch token
material.

Boundary: this package defines protocols only. The S3 and Secrets Manager implementations live in `budge.aws`;
tests substitute in-memory fakes.
"""

from budge.storage.repository import LeaseHeld, Repository
from budge.storage.secrets import SecretStore

__all__ = ['LeaseHeld', 'Repository', 'SecretStore']
