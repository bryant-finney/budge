"""`LambdaIngestionTrigger`: the Lambda async-invoke `budge.ingestion.IngestionTrigger` (spec §6, §7). Skeleton only.

Implemented in milestone 2. Locally the boto3 Lambda client reaches the ingestion container's Runtime Interface
Emulator through `AWS_ENDPOINT_URL_LAMBDA` (§12).
"""

from typing_extensions import override

from budge.ingestion import IngestionTrigger

__all__ = ['LambdaIngestionTrigger']

_MILESTONE_2 = 'LambdaIngestionTrigger is implemented in milestone 2'


# This adapter implements the trigger boundary's single operation.
class LambdaIngestionTrigger(IngestionTrigger):  # pylint: disable=too-few-public-methods
    """Starts ingestion with an async (`InvocationType=Event`) Lambda invoke."""

    function_name: str
    """The ingestion function's name or ARN (`function` under the local emulator, §12)."""

    def __init__(self, *, function_name: str) -> None:
        """Configure the trigger.

        Args:
            function_name: The ingestion function's name or ARN.
        """
        self.function_name = function_name

    @override
    def trigger(self, connection_id: str | None = None) -> None:
        raise NotImplementedError(_MILESTONE_2)
