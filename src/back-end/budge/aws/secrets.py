"""`SecretsManagerSecretStore`: the Secrets Manager `budge.storage.SecretStore` (spec §6). Skeleton only.

Implemented in milestone 2.
"""

__all__ = ['SecretsManagerSecretStore']

_MILESTONE_2 = 'SecretsManagerSecretStore is implemented in milestone 2'


class SecretsManagerSecretStore:
    """The AWS Secrets Manager implementation of `budge.storage.SecretStore`."""

    def get_access_token(self, connection_id: str) -> str | None:
        """See `budge.storage.SecretStore.get_access_token`."""
        raise NotImplementedError(_MILESTONE_2)

    def put_access_token(self, connection_id: str, token: str) -> None:
        """See `budge.storage.SecretStore.put_access_token`."""
        raise NotImplementedError(_MILESTONE_2)

    def delete_access_token(self, connection_id: str) -> None:
        """See `budge.storage.SecretStore.delete_access_token`."""
        raise NotImplementedError(_MILESTONE_2)
