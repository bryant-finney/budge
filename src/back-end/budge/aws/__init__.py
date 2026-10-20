"""AWS adapters: the AWS-backed implementations of the app's boundary protocols (spec §6).

This package holds the S3 `Repository`, the Secrets Manager `SecretStore`, and the Lambda async-invoke
`IngestionTrigger` the API uses to start ingestion.

Boundary: this is the only package that may import `boto3` or `botocore`. Everything else depends on the protocols
in `budge.storage` and `budge.ingestion`, so tests substitute fakes.

Each class subclasses the protocol it implements and marks every protocol method `@override`, so a signature that
drifts from its protocol is reported at the class definition. In milestone 1 they are skeleton stubs whose methods
raise `NotImplementedError`.
"""

from budge.aws.ingestion import LambdaIngestionTrigger
from budge.aws.repository import S3Repository
from budge.aws.secrets import SecretsManagerSecretStore

__all__ = ['LambdaIngestionTrigger', 'S3Repository', 'SecretsManagerSecretStore']
