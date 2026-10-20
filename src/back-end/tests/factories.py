"""Valid example models for tests, with validated overrides.

The domain models validate in strict mode, so the factories rebuild a model from its typed field values (a `frozenset`
stays a `frozenset`, a `datetime` stays a `datetime`), never from a python-mode `model_dump()`: that dump turns
`recurring_outflow_ids` into a sorted `list`, which strict validation rejects. Overrides must be correctly typed too.
"""

import datetime as dt

from budge.models import Account, BankConnection, Transaction

CREATED_AT = dt.datetime(2026, 10, 1, 12, 0, tzinfo=dt.UTC)

CONNECTION = BankConnection(
    connection_id='item-1',
    institution_id='ins_109508',
    institution_name='First Platypus Bank',
    linked_by='6f1c2a8e-0000-5000-8000-000000000001',
    plaid_env='sandbox',
    accounts=[Account(account_id='acc-1', name='Plaid Checking', mask='0000', type='depository', subtype='checking')],
    cursor=None,
    status='initializing',
    transactions_update_status=None,
    created_at=CREATED_AT,
    last_synced_at=None,
)
"""A freshly linked Sandbox connection, before its first sync."""

TRANSACTION = Transaction(
    transaction_id='txn-1',
    connection_id='item-1',
    account_id='acc-1',
    date=dt.date(2026, 10, 6),
    authorized_date=dt.date(2026, 10, 5),
    effective_date=dt.date(2026, 10, 5),
    datetime=dt.datetime(2026, 10, 6, 15, 10, 9, tzinfo=dt.UTC),
    amount=28.34,
    currency='USD',
    name='Dd Doordash Burgerkin',
    merchant_name='Burger King',
    pfc_primary='FOOD_AND_DRINK',
    pfc_detailed='FOOD_AND_DRINK_FAST_FOOD',
    pending=False,
    pending_transaction_id=None,
    is_discretionary=True,
    excluded_reason='none',
)
"""A posted, discretionary purchase."""


def make_connection(**update: object) -> BankConnection:
    """Return a deep copy of `CONNECTION` with `update` applied, validated (unlike `model_copy(update=...)`)."""
    return BankConnection.model_validate({**dict(CONNECTION.model_copy(deep=True)), **update})


def make_transaction(**update: object) -> Transaction:
    """Return a deep copy of `TRANSACTION` with `update` applied, validated (unlike `model_copy(update=...)`)."""
    return Transaction.model_validate({**dict(TRANSACTION.model_copy(deep=True)), **update})
