"""budge: trailing-7-day discretionary spend, computed from Plaid transactions.

The back end is one package deployed as one container image to two AWS Lambdas (spec §4, §12):

- `budge.api`: the FastAPI application behind API Gateway (served through Mangum).
- `budge.ingestion`: the ingestion Lambda that pulls transactions from Plaid into storage.
- `budge.storage`: the `Repository` and `SecretStore` protocols the rest of the app depends on.
- `budge.aws`: the AWS-backed implementations of those protocols; the only package that imports `boto3`.
- `budge.plaid_client`: the Plaid API client used by onboarding and ingestion.
- `budge.classify`: the pure exclusion classifier (no I/O).

The installed distribution's version is exposed as `__version__`:

>>> import importlib.metadata
>>> import budge
>>> budge.__version__ == importlib.metadata.version('budge')
True

When `budge/` is importable but not installed, so no `budge-*.dist-info` exists, `__version__` stays `'0.0.0'`
instead of raising at import time.
"""

import contextlib
import importlib.metadata

__version__: str = '0.0.0'
"""The version of the installed `budge` distribution, or `'0.0.0'` if it isn't installed.

`'0.0.0'` matches `fallback-version` in `pyproject.toml`, so "not installed" and "installed without `.git`" report
the same version.
"""

# e.g. only the `budge/` source copied into an image: keep the default, so importing can't crash the Lambda handlers
with contextlib.suppress(importlib.metadata.PackageNotFoundError):
    __version__ = importlib.metadata.version(__name__)
