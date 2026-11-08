"""The API's configuration and its boundary implementations, each provided to routes as a FastAPI dependency.

Routes never read `os.environ` or construct an AWS adapter themselves: they depend on `get_auth_settings` and
`get_secret_store`, which tests replace through `app.dependency_overrides`.

Environment (set by Pulumi on the API Lambda, and by `docker compose` locally; spec §12 Config):

- `BUDGE_GOOGLE_CLIENT_ID`: the Google OAuth client ID, the `aud` every Google ID token must carry.
- `BUDGE_ALLOWED_GOOGLE_SUBS`: the allowlisted Google account `sub`s, comma-separated.
"""

import functools
import os
from collections.abc import Mapping
from typing import Final, Self

from pydantic import BaseModel, ConfigDict, Field

from budge.aws import SecretsManagerSecretStore
from budge.storage import SecretStore

__all__ = [
    'ALLOWED_SUBS_VAR',
    'CLIENT_ID_VAR',
    'AuthSettings',
    'get_auth_settings',
    'get_secret_store',
]

CLIENT_ID_VAR: Final = 'BUDGE_GOOGLE_CLIENT_ID'
"""The environment variable that holds the Google OAuth client ID."""

ALLOWED_SUBS_VAR: Final = 'BUDGE_ALLOWED_GOOGLE_SUBS'
"""The environment variable that holds the comma-separated allowlist of Google `sub`s."""


class AuthSettings(BaseModel):
    """Who may sign in, and with which Google OAuth client (spec §8 Auth)."""

    model_config = ConfigDict(extra='forbid', frozen=True, strict=True, use_attribute_docstrings=True)

    google_client_id: str = Field(min_length=1)
    """The Google OAuth client ID: a Google ID token's `aud` must equal it."""

    allowed_subs: frozenset[str]
    """The Google account `sub`s allowed to use the app. Removing one revokes that account's sessions."""

    @classmethod
    def from_environ(cls, environ: Mapping[str, str]) -> Self:
        """Read the settings from `CLIENT_ID_VAR` and `ALLOWED_SUBS_VAR`.

        Blank entries in the allowlist are ignored, so an empty or unset allowlist admits nobody.

        Args:
            environ: The environment, such as `os.environ`.

        Returns:
            The settings.

        Raises:
            KeyError: `CLIENT_ID_VAR` is unset.

        >>> AuthSettings.from_environ({CLIENT_ID_VAR: 'id', ALLOWED_SUBS_VAR: ' 1, 2,,'}).allowed_subs == {'1', '2'}
        True
        """
        subs = environ.get(ALLOWED_SUBS_VAR, '').split(',')
        return cls(
            google_client_id=environ[CLIENT_ID_VAR],
            allowed_subs=frozenset(sub.strip() for sub in subs if sub.strip()),
        )


@functools.cache
def get_auth_settings() -> AuthSettings:
    """Return the settings from the process environment, read once per process (once per Lambda execution environment).

    A dependency: tests override it with their own `AuthSettings`.
    """
    return AuthSettings.from_environ(os.environ)


@functools.cache
def get_secret_store() -> SecretStore:
    """Return the process's `SecretStore`: the Secrets Manager one (spec §6), created once per process.

    A dependency: tests override it with an in-memory fake.
    """
    return SecretsManagerSecretStore()
