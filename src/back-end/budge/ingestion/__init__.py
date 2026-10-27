"""Ingestion: the Lambda that pulls new transactions for each connection and writes them to storage (spec §4, §7, §9).

It runs on an EventBridge Scheduler cadence and on async invokes from the API. This package also defines the
`IngestionTrigger` protocol the API uses to start ingestion; its Lambda async-invoke implementation lives in
`budge.aws`.

Boundary: ingestion reaches storage, secrets, and Plaid only through the `budge.storage` protocols and
`budge.plaid_client`; it never imports `boto3`.
"""

from budge.ingestion.summary import FAILED_OUTCOMES, Outcome, RunResult, RunSummary, count_failed
from budge.ingestion.trigger import IngestionTrigger

__all__ = ['FAILED_OUTCOMES', 'IngestionTrigger', 'Outcome', 'RunResult', 'RunSummary', 'count_failed']
