"""Tests for the stub ingestion Lambda handler (spec §9, §12: Scheduler and async-invoke payloads)."""

import json
import logging

import pytest
from mangum.types import LambdaContext

from budge.ingestion.handler import handler

SCHEDULER_EVENT: dict[str, object] = {
    'execution_id': 'c0ffee00-0000-4000-8000-000000000001',
    'scheduled_time': '2026-10-17T16:00:00Z',
}
"""Illustrative Scheduler target input built from its context attributes; the real `Input` is fixed in M2/M4."""


@pytest.mark.parametrize(
    'event',
    [
        pytest.param(SCHEDULER_EVENT, id='scheduler'),
        pytest.param({}, id='async-invoke-all'),
        pytest.param({'connection_ids': ['item-1']}, id='async-invoke-one'),
    ],
)
def test_handler_returns_and_logs_an_empty_summary(
    event: dict[str, object], lambda_context: LambdaContext, caplog: pytest.LogCaptureFixture
) -> None:
    """Milestone 1's stub processes nothing: it returns `{}` and logs that summary as one JSON line."""
    with caplog.at_level(logging.INFO, logger='budge.ingestion.handler'):
        summary = handler(event, lambda_context)

    assert summary == {}
    assert [json.loads(record.getMessage()) for record in caplog.records] == [{}]
