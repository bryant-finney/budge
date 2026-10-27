"""The ingestion run summary: one result per connection, returned and logged in one record (spec §9, §12)."""

from typing import Final, Literal, TypedDict

__all__ = ['FAILED_OUTCOMES', 'Outcome', 'RunResult', 'RunSummary', 'count_failed']

Outcome = Literal['ok', 'skipped_locked', 'not_ready', 'login_required', 'error']
"""How one connection's sync ended (spec §9)."""

FAILED_OUTCOMES: Final[frozenset[Outcome]] = frozenset({'error', 'login_required'})
"""The outcomes §12's alarm counts: the connection needs attention before it can sync again."""


class RunResult(TypedDict):
    """One connection's entry in the run summary (spec §9)."""

    outcome: Outcome
    added: int
    modified: int
    removed: int
    error_code: str | None


RunSummary = dict[str, RunResult]
"""`{connection_id: RunResult}` for every connection a run processed."""


def count_failed(summary: RunSummary) -> int:
    """Count the connections whose outcome is in `FAILED_OUTCOMES`.

    The ingestion handler logs this count as `failed_connections`, the field §12's metric filter reads, because the
    summary's own keys are connection ids and give the filter no fixed path to each `outcome`.

    Args:
        summary: The run summary to inspect.

    Returns:
        The number of connections that ended in `error` or `login_required`.

    >>> ok = {'outcome': 'ok', 'added': 2, 'modified': 0, 'removed': 0, 'error_code': None}
    >>> relink = {**ok, 'outcome': 'login_required', 'added': 0, 'error_code': 'ITEM_LOGIN_REQUIRED'}
    >>> count_failed({'item-1': ok, 'item-2': relink})
    1
    """
    return sum(result['outcome'] in FAILED_OUTCOMES for result in summary.values())
