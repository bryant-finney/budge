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

The value comes from `budge/_version.py`, which every build and `uv sync` generates (and git ignores). Without that
file, e.g. when only the committed `budge/` source is copied into an image, `__version__` is `'0.0.0'`, matching
`fallback-version` in `pyproject.toml`, so importing never fails.
"""

try:
    from budge._version import __version__
except ModuleNotFoundError:
    __version__ = '0.0.0'

__all__ = ['__version__']
