"""Tests for the API's configuration dependencies (`budge.api.config`)."""

from collections.abc import Iterator

import pytest

from budge.api.config import (
    ALLOWED_SUBS_VAR,
    CLIENT_ID_VAR,
    AuthSettings,
    get_auth_settings,
    get_secret_store,
)
from budge.aws import SecretsManagerSecretStore


@pytest.fixture
def fresh_settings() -> Iterator[None]:
    """Clear the per-process settings cache before and after the test."""
    get_auth_settings.cache_clear()
    yield
    get_auth_settings.cache_clear()


@pytest.mark.usefixtures('fresh_settings')
def test_settings_come_from_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """`get_auth_settings` reads the client ID and the comma-separated allowlist, once per process."""
    monkeypatch.setenv(CLIENT_ID_VAR, 'client.apps.googleusercontent.com')
    monkeypatch.setenv(ALLOWED_SUBS_VAR, '111, 222')

    settings = get_auth_settings()

    assert settings == AuthSettings(
        google_client_id='client.apps.googleusercontent.com', allowed_subs=frozenset({'111', '222'})
    )
    monkeypatch.setenv(ALLOWED_SUBS_VAR, '333')
    assert get_auth_settings() is settings


def test_an_unset_allowlist_admits_nobody() -> None:
    """With no allowlist set, no `sub` is allowed."""
    assert AuthSettings.from_environ({CLIENT_ID_VAR: 'id'}).allowed_subs == frozenset()


def test_the_client_id_is_required() -> None:
    """Without a client ID there is no `aud` to check, so reading the settings fails."""
    with pytest.raises(KeyError, match=CLIENT_ID_VAR):
        AuthSettings.from_environ({ALLOWED_SUBS_VAR: '111'})


def test_the_client_id_must_not_be_blank() -> None:
    """An empty client ID is rejected rather than matching an empty `aud`."""
    with pytest.raises(ValueError, match='google_client_id'):
        AuthSettings.from_environ({CLIENT_ID_VAR: ''})


def test_the_secret_store_is_the_secrets_manager_one() -> None:
    """Outside tests, the API's secret store is the Secrets Manager adapter, created once per process."""
    store = get_secret_store()

    assert isinstance(store, SecretsManagerSecretStore)
    assert get_secret_store() is store
