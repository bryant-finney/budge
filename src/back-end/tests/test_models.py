"""Tests for the §6 domain models and the classifier vocabulary."""

import ast
import datetime as dt
import inspect
import json
from typing import get_args

import pytest
from pydantic import BaseModel, ValidationError

import budge.classify
import budge.models
from budge.classify import COUNT, NO_PFC_CATEGORY, ExcludedReason
from budge.models import Account, BankConnection, Transaction
from tests.factories import CONNECTION, TRANSACTION, make_connection, make_transaction

SYNCED = make_connection(
    cursor='cursor-1',
    status='healthy',
    transactions_update_status='HISTORICAL_UPDATE_COMPLETE',
    recurring_outflow_ids=frozenset({'txn-9', 'txn-2', 'txn-5'}),
    last_synced_at=dt.datetime(2026, 10, 2, 8, 0, tzinfo=dt.UTC),
)
UNCATEGORIZED = make_transaction(
    authorized_date=None,
    effective_date=TRANSACTION.date,
    datetime=None,
    merchant_name=None,
    pfc_primary=None,
    pfc_detailed=None,
)


@pytest.mark.parametrize('model', [CONNECTION, SYNCED, TRANSACTION, UNCATEGORIZED])
def test_models_round_trip_through_json(model: BaseModel) -> None:
    """Every model survives `model_dump_json` -> `model_validate_json` unchanged (as S3 storage will use it)."""
    assert type(model).model_validate_json(model.model_dump_json()) == model


def test_transaction_accepts_null_pfc_fields() -> None:
    """A transaction with no Plaid category (or other nullable fields) is valid (spec §5: charted as UNCATEGORIZED)."""
    assert UNCATEGORIZED.pfc_primary is None
    assert UNCATEGORIZED.pfc_detailed is None


def test_recurring_outflow_ids_serialize_sorted() -> None:
    """The id set serializes as a sorted list, so stored metadata is deterministic."""
    assert json.loads(SYNCED.model_dump_json())['recurring_outflow_ids'] == ['txn-2', 'txn-5', 'txn-9']


def test_recurring_outflow_ids_default_to_empty() -> None:
    """A new connection has no recurring ids until `/transactions/recurring/get` runs."""
    assert CONNECTION.recurring_outflow_ids == frozenset()


@pytest.mark.parametrize(
    ('field', 'value'),
    [
        ('status', 'syncing'),
        ('plaid_env', 'development'),
        ('transactions_update_status', 'DONE'),
        ('created_at', dt.datetime(2026, 10, 1, 12, 0)),  # naive on purpose
    ],
)
def test_connection_rejects_invalid_values(field: str, value: object) -> None:
    """Unknown `Literal` values and naive datetimes are rejected."""
    with pytest.raises(ValidationError):
        make_connection(**{field: value})


@pytest.mark.parametrize(
    ('field', 'value'),
    [
        ('excluded_reason', 'refund'),
        ('datetime', dt.datetime(2026, 10, 6, 15, 10)),  # naive on purpose
        ('amount', float('nan')),
        ('amount', float('inf')),
        ('amount', float('-inf')),
    ],
)
def test_transaction_rejects_invalid_values(field: str, value: object) -> None:
    """Unknown `excluded_reason` values, naive datetimes, and non-finite amounts are rejected."""
    with pytest.raises(ValidationError):
        make_transaction(**{field: value})


@pytest.mark.parametrize('field', ['status', 'plaid_env'])
def test_assignment_is_validated(field: str) -> None:
    """Assigning an invalid value after construction is rejected too (`validate_assignment`)."""
    connection = make_connection()

    with pytest.raises(ValidationError):
        setattr(connection, field, 'bogus')


@pytest.mark.parametrize('model', [Account, BankConnection, Transaction])
def test_no_model_has_an_access_token_field(model: type[BaseModel]) -> None:
    """Token material never lives on a model (spec §6)."""
    assert 'access_token' not in model.model_fields


@pytest.mark.parametrize('example', [CONNECTION, TRANSACTION, CONNECTION.accounts[0]])
def test_unknown_fields_are_rejected(example: BaseModel) -> None:
    """`extra='forbid'`: data carrying an `access_token` (or any unknown field) fails validation."""
    with pytest.raises(ValidationError, match='extra'):
        type(example).model_validate({**example.model_dump(), 'access_token': 'access-sandbox-0000'})


def test_classifier_vocabulary_matches_spec() -> None:
    """`ExcludedReason`, `COUNT`, and `NO_PFC_CATEGORY` are exactly the spec §6/§9/Appendix A values."""
    assert get_args(ExcludedReason) == (
        'inflow',
        'transfer',
        'cc_payment',
        'bill',
        'bank_fee',
        'medical',
        'tax',
        'recurring',
        'none',
    )
    assert COUNT == 'count'
    assert NO_PFC_CATEGORY == 'UNCATEGORIZED'


def test_models_is_a_leaf_module() -> None:
    """`budge.models` imports nothing from `budge`, so the classifier can import `Transaction` without a cycle."""
    imported: set[str] = set()
    for node in ast.walk(ast.parse(inspect.getsource(budge.models))):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported.add(node.module)

    assert sorted(name for name in imported if name.split('.')[0] == 'budge') == []


def test_classify_re_exports_the_models_vocabulary() -> None:
    """`budge.classify.ExcludedReason` is the very alias the `Transaction` model uses."""
    assert budge.classify.ExcludedReason is budge.models.ExcludedReason
