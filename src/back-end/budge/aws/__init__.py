"""AWS adapters: the AWS-backed implementations of the app's boundary protocols (spec §6).

This package holds the S3 `Repository`, the Secrets Manager `SecretStore`, and the Lambda async-invoke
`IngestionTrigger` the API uses to start ingestion.

Boundary: this is the only package that may import `boto3` or `botocore`. Everything else depends on the protocols
in `budge.storage` and `budge.ingestion`, so tests substitute fakes.
"""
