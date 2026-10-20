"""Exclusion classifier: decides whether a transaction counts toward discretionary spend (spec §5, §9, Appendix A).

The verdict comes from the transaction's sign, its Plaid personal finance category (PFC v2), and whether its stream
is a recurring outflow.

Boundary: pure logic with no I/O. It takes a `budge.models.Transaction` and the connection's recurring outflow ids and
returns a verdict, so it is table-tested against every PFC v2 detailed category.

Milestone 1 defines only the vocabulary below; `classify()` and the `PFC_RULES` table arrive in milestone 2.
`ExcludedReason` is a `budge.models.Transaction` field type, so it is defined in the leaf module `budge.models` and
re-exported here: the classifier imports the models, never the other way round.

>>> from typing import get_args
>>> get_args(ExcludedReason)[-1]
'none'
>>> COUNT, NO_PFC_CATEGORY
('count', 'UNCATEGORIZED')
"""

from typing import Final

from budge.models import ExcludedReason

__all__ = ['COUNT', 'NO_PFC_CATEGORY', 'ExcludedReason']

COUNT: Final = 'count'
"""`PFC_RULES` sentinel: ends the PFC lookup as spend; the recurring check still applies (spec §9)."""

NO_PFC_CATEGORY: Final = 'UNCATEGORIZED'
"""Chart key for a transaction with no Plaid category; it can't collide with Plaid's `OTHER` primary (Appendix A)."""
