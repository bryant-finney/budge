"""Tests for the boundary protocols: the fakes and the `budge.aws` stubs conform, and the fakes honor the contract."""

import datetime as dt
from collections.abc import Callable, Iterable

import pytest

from budge.aws import LambdaIngestionTrigger, S3Repository, SecretsManagerSecretStore
from budge.ingestion import IngestionTrigger
from budge.models import Transaction
from budge.storage import LeaseHeld, Repository, SecretStore
from tests.factories import TRANSACTION, make_connection, make_transaction
from tests.fakes import FakeIngestionTrigger, FakeRepository, FakeSecretStore

WINDOW_START = dt.date(2026, 10, 5)
WINDOW_END = dt.date(2026, 10, 11)


def by_id(rows: Iterable[Transaction]) -> list[Transaction]:
    """Sort rows by `transaction_id`: `Repository.get_transactions` promises no order (and models aren't hashable)."""
    return sorted(rows, key=lambda row: row.transaction_id)


@pytest.fixture
def repo() -> Repository:
    """A Sandbox-scoped fake repository, seen only through the `Repository` protocol."""
    return FakeRepository('sandbox')


@pytest.fixture
def secrets() -> SecretStore:
    """A fake secret store, seen only through the `SecretStore` protocol."""
    return FakeSecretStore()


def test_implementations_conform_to_protocols() -> None:
    """The fakes and the AWS stubs implement the protocols; mypy and pyright strict check these annotations."""
    repositories: list[Repository] = [FakeRepository(), S3Repository(bucket='budge-data', plaid_env='sandbox')]
    secret_stores: list[SecretStore] = [FakeSecretStore(), SecretsManagerSecretStore()]
    triggers: list[IngestionTrigger] = [FakeIngestionTrigger(), LambdaIngestionTrigger(function_name='function')]

    assert len(repositories) == len(secret_stores) == len(triggers)


def test_repository_round_trips_connections_as_copies(repo: Repository) -> None:
    """A saved connection reads back equal, and mutating the returned model doesn't change what's stored."""
    connection = make_connection()
    repo.save_connection(connection)

    fetched = repo.get_connection('item-1')
    assert fetched == connection
    assert fetched is not None
    fetched.status = 'healthy'

    assert repo.get_connection('item-1') == connection
    assert repo.list_connections() == [connection]


def test_repository_is_scoped_to_its_environment(repo: Repository) -> None:
    """The other environment's connections and their transactions are invisible (spec §6)."""
    repo.save_connection(make_connection(connection_id='item-prod', plaid_env='production'))
    repo.put_transaction_rows('item-prod', [make_transaction(connection_id='item-prod')])

    assert repo.list_connections() == []
    assert repo.get_connection('item-prod') is None
    assert repo.get_transactions(WINDOW_START, WINDOW_END, discretionary_only=False) == []


def test_get_transactions_is_inclusive_on_effective_date(repo: Repository) -> None:
    """The window includes both endpoints and filters on `effective_date`, not `date` (spec §5, §6)."""
    first = make_transaction(transaction_id='first', effective_date=WINDOW_START)
    last = make_transaction(transaction_id='last', date=WINDOW_END, authorized_date=None, effective_date=WINDOW_END)
    before = make_transaction(transaction_id='before', effective_date=WINDOW_START - dt.timedelta(days=1))
    after = make_transaction(transaction_id='after', effective_date=WINDOW_END + dt.timedelta(days=1))
    excluded = make_transaction(transaction_id='excluded', is_discretionary=False, excluded_reason='medical')
    repo.save_connection(make_connection())
    repo.put_transaction_rows('item-1', [first, last, before, after, excluded])

    assert by_id(repo.get_transactions(WINDOW_START, WINDOW_END)) == by_id([first, last])
    assert by_id(repo.get_transactions(WINDOW_START, WINDOW_END, discretionary_only=False)) == by_id(
        [first, last, excluded]
    )


def test_delete_connection_removes_rows_and_is_idempotent(repo: Repository) -> None:
    """Deleting drops metadata and transactions; deleting again (or an unknown id) is a no-op."""
    repo.save_connection(make_connection())
    repo.put_transaction_rows('item-1', [TRANSACTION])

    repo.delete_connection('item-1')
    repo.delete_connection('item-1')

    assert repo.get_connection('item-1') is None
    assert repo.get_transaction_rows('item-1') == []


def test_lock_raises_lease_held_while_held(repo: Repository) -> None:
    """A second holder gets `LeaseHeld`; the lease is released when the block exits."""
    with repo.lock('connection-item-1'), pytest.raises(LeaseHeld) as excinfo, repo.lock('connection-item-1'):
        pass  # never reached: entering the inner lock raises

    assert excinfo.value.name == 'connection-item-1'
    with repo.lock('connection-item-1'):
        pass


def test_lock_is_released_on_exception(repo: Repository) -> None:
    """An exception inside the block still releases the lease (spec §6)."""
    with pytest.raises(RuntimeError), repo.lock('onboarding'):
        raise RuntimeError

    with repo.lock('onboarding'):
        pass


def test_secret_store_round_trip(secrets: SecretStore) -> None:
    """Tokens round-trip; a missing token reads as `None`; deleting a missing secret is a no-op (spec §6, §7)."""
    secrets.put_access_token('item-1', 'access-sandbox-0000')
    assert secrets.get_access_token('item-1') == 'access-sandbox-0000'

    secrets.delete_access_token('item-1')
    secrets.delete_access_token('item-1')

    assert secrets.get_access_token('item-1') is None


def test_ingestion_trigger_records_requests() -> None:
    """The fake records one entry per request: one connection's id, or `None` for all connections."""
    trigger = FakeIngestionTrigger()

    trigger.trigger('item-1')
    trigger.trigger()

    assert trigger.calls == ['item-1', None]


def _stub_calls() -> list[Callable[[], object]]:
    repo = S3Repository(bucket='budge-data', plaid_env='sandbox')
    secrets = SecretsManagerSecretStore()
    trigger = LambdaIngestionTrigger(function_name='function')
    return [
        repo.list_connections,
        lambda: repo.get_connection('item-1'),
        lambda: repo.save_connection(make_connection()),
        lambda: repo.delete_connection('item-1'),
        lambda: repo.get_transaction_rows('item-1'),
        lambda: repo.put_transaction_rows('item-1', []),
        lambda: repo.get_transactions(WINDOW_START, WINDOW_END),
        lambda: repo.lock('onboarding'),
        lambda: secrets.get_access_token('item-1'),
        lambda: secrets.put_access_token('item-1', 'access-sandbox-0000'),
        lambda: secrets.delete_access_token('item-1'),
        trigger.trigger,
    ]


@pytest.mark.parametrize('call', _stub_calls())
def test_aws_stubs_are_not_implemented_yet(call: Callable[[], object]) -> None:
    """Every `budge.aws` method is a milestone-2 stub."""
    with pytest.raises(NotImplementedError, match='milestone 2'):
        call()


def test_aws_stubs_keep_their_configuration() -> None:
    """The stubs record the configuration milestone 2 will use."""
    repo = S3Repository(bucket='budge-data', plaid_env='production')
    trigger = LambdaIngestionTrigger(function_name='function')

    assert (repo.bucket, repo.plaid_env, trigger.function_name) == ('budge-data', 'production', 'function')
