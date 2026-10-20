"""Domain models: the spec §6 entities, as Pydantic models shared by storage, ingestion, and the API.

Every model validates in pydantic's strict mode, forbids unknown fields, and re-validates on assignment. Strict mode
does no type coercion: python-mode input must already have each field's type, so `amount='28.34'` or `pending='yes'`
fails instead of silently becoming `28.34` or `True`, and a mapping bug in Plaid normalization surfaces at the model.
JSON input (`model_validate_json`) still parses dates, datetimes, and the `recurring_outflow_ids` list, so stored data
round-trips through `model_dump_json`; a python-mode `model_dump()` doesn't, because it turns that `frozenset` into a
list.

No model has an `access_token` field: token material lives only behind `budge.storage.SecretStore` (spec §6), and
`extra='forbid'` rejects stored or incoming data that tries to carry one.

This is a leaf module: it imports nothing from `budge`, so every other package (the classifier included) can import
the models without an import cycle. That is why `ExcludedReason`, a `Transaction` field type, is defined here and
re-exported by `budge.classify`.

>>> Account(account_id='acc-1', name=None, mask='0000', type='depository', subtype=None).mask
'0000'
"""

import datetime as dt
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, FiniteFloat, field_serializer

__all__ = [
    'Account',
    'BankConnection',
    'ConnectionStatus',
    'DomainModel',
    'ExcludedReason',
    'PlaidEnv',
    'Transaction',
    'TransactionsUpdateStatus',
]

PlaidEnv = Literal['sandbox', 'production']
"""The Plaid environment a connection was linked in (spec §6, §11)."""

ConnectionStatus = Literal['initializing', 'healthy', 'login_required']
"""A connection's sync health, surfaced by `GET /connections` (spec §6, §7)."""

TransactionsUpdateStatus = Literal[
    'TRANSACTIONS_UPDATE_STATUS_UNKNOWN',
    'NOT_READY',
    'INITIAL_UPDATE_COMPLETE',
    'HISTORICAL_UPDATE_COMPLETE',
]
"""Plaid's `/transactions/sync` `transactions_update_status` values (spec §7)."""

ExcludedReason = Literal['inflow', 'transfer', 'cc_payment', 'bill', 'bank_fee', 'medical', 'tax', 'recurring', 'none']
"""Why a transaction is excluded from discretionary spend; `'none'` means it counts (spec §6, §9).

Part of the classifier's vocabulary, re-exported by `budge.classify`.
"""


class DomainModel(BaseModel):
    """Base for every `budge` domain model: strict, closed, and re-validated on assignment.

    `strict=True` disables type coercion (a string is never a float, bool, or date), `extra='forbid'` rejects unknown
    fields, and `validate_assignment=True` applies both to later assignments. Nested models still accept a `dict`.
    """

    model_config = ConfigDict(extra='forbid', validate_assignment=True, use_attribute_docstrings=True, strict=True)


class Account(DomainModel):
    """One account at a linked institution, as Plaid Link reports it; used for the duplicate-account check (§7)."""

    account_id: str
    """Plaid's `account_id`."""

    name: str | None
    """The account name; Plaid may omit it."""

    mask: str | None
    """The last few characters of the account number. It is never treated as an account number (§7)."""

    type: str
    """Plaid's account type, e.g. `depository` or `credit`."""

    subtype: str | None
    """Plaid's account subtype, e.g. `checking`."""


class BankConnection(DomainModel):
    """One Plaid Item: one login at one institution (spec §6).

    Saved before its first sync (§7 onboarding step 4), so `cursor`, `transactions_update_status`, and
    `last_synced_at` are `None` until ingestion first runs. `recurring_outflow_ids` is a `frozenset` because the
    classifier only tests membership; it serializes as a sorted list, so stored metadata is deterministic.
    """

    connection_id: str
    """Plaid's `item_id`."""

    institution_id: str
    """Plaid's `institution_id`."""

    institution_name: str
    """The institution's display name."""

    linked_by: str
    """The linking user's Plaid `client_user_id` (a UUIDv5 of their Google `sub`, §7)."""

    plaid_env: PlaidEnv
    """The Plaid environment the connection was linked in; repositories only see their own environment."""

    accounts: list[Account]
    """The accounts selected in Link."""

    cursor: str | None
    """The `/transactions/sync` cursor, persisted only after a complete sync loop; `None` before the first sync."""

    status: ConnectionStatus
    """The connection's sync health."""

    transactions_update_status: TransactionsUpdateStatus | None
    """The last `transactions_update_status` seen from Plaid; `None` before the first sync."""

    recurring_outflow_ids: frozenset[str] = frozenset()
    """Transaction ids in Plaid's recurring outflow streams, from `/transactions/recurring/get`."""

    created_at: AwareDatetime
    """When the connection was linked (timezone-aware)."""

    last_synced_at: AwareDatetime | None
    """When ingestion last completed for this connection (timezone-aware); `None` before the first sync."""

    @field_serializer('recurring_outflow_ids')
    def _serialize_recurring_outflow_ids(self, ids: frozenset[str]) -> list[str]:
        return sorted(ids)


class Transaction(DomainModel):
    """One normalized transaction (spec §5, §6): spend is positive, and money stays a float in dollars."""

    transaction_id: str
    """Plaid's `transaction_id`."""

    connection_id: str
    """The owning `BankConnection.connection_id`."""

    account_id: str
    """Plaid's `account_id`."""

    date: dt.date
    """Plaid's `date`: the occurred date if pending, the posted date if posted."""

    authorized_date: dt.date | None
    """Plaid's `authorized_date`, when the transaction was authorized."""

    effective_date: dt.date
    """`authorized_date ?? date`: the date the 7-day window filters and buckets on (§5)."""

    datetime: AwareDatetime | None
    """Plaid's `datetime`, when available."""

    # a plain `float` that rejects NaN and ±inf: pydantic writes NaN to JSON as `null`, which then fails to read back
    # and would make the connection's whole stored `transactions.json.gz` unreadable
    amount: FiniteFloat
    """Dollars, normalized so spend (money out) is positive; always finite; no `Decimal` (§5)."""

    # open for milestone 2's normalization (spec §6 doesn't settle it): Plaid's `iso_currency_code` is `null` whenever
    # `unofficial_currency_code` is set, so map such a row deliberately (fall back to the unofficial code, make this
    # field nullable, or drop and log the row) rather than let it fail validation by accident
    currency: str
    """The ISO 4217 currency code."""

    name: str
    """Plaid's transaction description."""

    merchant_name: str | None
    """The merchant's name, when Plaid identifies one."""

    pfc_primary: str | None
    """The Plaid personal finance category (v2) primary value."""

    pfc_detailed: str | None
    """The Plaid personal finance category (v2) detailed value."""

    pending: bool
    """Whether the transaction is still pending."""

    pending_transaction_id: str | None
    """On a posted transaction, the id of the pending transaction it replaces."""

    is_discretionary: bool
    """The classifier's verdict: whether the row counts toward discretionary spend (§9)."""

    excluded_reason: ExcludedReason
    """Why the row is excluded, or `'none'` when it counts (§9)."""
