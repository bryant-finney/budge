"""The ingestion Lambda's entrypoint.

**Lambda handler string: `budge.ingestion.handler.handler`.**

EventBridge Scheduler (all connections) and the API's async invokes (all, or one connection) call `handler`
(spec §4, §9). Milestone 1 is a stub: it processes nothing and returns an empty run summary. Milestone 2 replaces the
body with `run_ingestion(connection_ids)`.
"""

import json
import logging
from collections.abc import Mapping

from budge.ingestion.summary import RunSummary

__all__ = ['handler']

logger = logging.getLogger(__name__)
# the run summary is the function's one operational log line (spec §9), so it must survive the Lambda runtime's
# default root level
logger.setLevel(logging.INFO)


def handler(event: Mapping[str, object], context: object) -> RunSummary:
    """Run ingestion for the connections the event names, then return and log the run summary.

    Args:
        event: The invocation payload: a Scheduler target input, or the API's async-invoke payload.
        context: The Lambda context object (unused until a typed context is adopted in milestone 2).

    Returns:
        `{connection_id: RunResult}`; empty in milestone 1.

    >>> handler({}, None)
    {}
    """
    summary: RunSummary = {}
    logger.info('%s', json.dumps(summary, sort_keys=True, separators=(',', ':')))
    return summary
