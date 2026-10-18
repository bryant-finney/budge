"""The ingestion run summary: one result per connection, returned and logged as one JSON line (spec §9)."""

from typing import Literal, TypedDict

__all__ = ['Outcome', 'RunResult', 'RunSummary']

Outcome = Literal['ok', 'skipped_locked', 'not_ready', 'login_required', 'error']
"""How one connection's sync ended (spec §9)."""


class RunResult(TypedDict):
    """One connection's entry in the run summary (spec §9)."""

    outcome: Outcome
    added: int
    modified: int
    removed: int
    error_code: str | None


RunSummary = dict[str, RunResult]
"""`{connection_id: RunResult}` for every connection a run processed."""
