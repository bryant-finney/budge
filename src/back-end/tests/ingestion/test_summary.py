"""Tests for the ingestion run summary helpers (spec §9, §12)."""

import pytest

from budge.ingestion.summary import FAILED_OUTCOMES, Outcome, RunResult, RunSummary, count_failed


def _result(outcome: Outcome) -> RunResult:
    """Build a run result with the given outcome and no row changes."""
    return {'outcome': outcome, 'added': 0, 'modified': 0, 'removed': 0, 'error_code': None}


def test_failed_outcomes_are_error_and_login_required() -> None:
    """§12's metric filter counts exactly the `error` and `login_required` outcomes."""
    assert frozenset({'error', 'login_required'}) == FAILED_OUTCOMES


@pytest.mark.parametrize(
    ('outcome', 'expected'),
    [
        pytest.param('ok', 0, id='ok'),
        pytest.param('skipped_locked', 0, id='skipped_locked'),
        pytest.param('not_ready', 0, id='not_ready'),
        pytest.param('login_required', 1, id='login_required'),
        pytest.param('error', 1, id='error'),
    ],
)
def test_count_failed_classifies_each_outcome(outcome: Outcome, expected: int) -> None:
    """Each §9 outcome counts as a failure exactly when it is `error` or `login_required`."""
    assert count_failed({'item-1': _result(outcome)}) == expected


def test_count_failed_counts_across_connections() -> None:
    """A summary with mixed outcomes counts every failed connection once."""
    failed: RunSummary = {
        'item-2': _result('error'),
        'item-3': _result('login_required'),
        'item-5': {'outcome': 'error', 'added': 0, 'modified': 0, 'removed': 0, 'error_code': 'INTERNAL_SERVER_ERROR'},
    }
    passed: RunSummary = {'item-1': _result('ok'), 'item-4': _result('skipped_locked'), 'item-6': _result('not_ready')}

    assert count_failed(passed | failed) == len(failed)


def test_count_failed_of_an_empty_summary_is_zero() -> None:
    """A run that processed no connections has no failures."""
    assert count_failed({}) == 0
