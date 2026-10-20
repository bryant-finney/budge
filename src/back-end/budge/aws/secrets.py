"""`SecretsManagerSecretStore`: the Secrets Manager `budge.storage.SecretStore` (spec §6). Skeleton only.

Implemented in milestone 2.
"""

from typing_extensions import override

from budge.storage import SecretStore

__all__ = ['SecretsManagerSecretStore']

_MILESTONE_2 = 'SecretsManagerSecretStore is implemented in milestone 2'


class SecretsManagerSecretStore(SecretStore):
    """The AWS Secrets Manager implementation of `budge.storage.SecretStore`."""

    @override
    def get_access_token(self, connection_id: str) -> str | None:
        raise NotImplementedError(_MILESTONE_2)

    @override
    def put_access_token(self, connection_id: str, token: str) -> None:
        raise NotImplementedError(_MILESTONE_2)

    @override
    def delete_access_token(self, connection_id: str) -> None:
        raise NotImplementedError(_MILESTONE_2)
