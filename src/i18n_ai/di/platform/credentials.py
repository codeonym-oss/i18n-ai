from dishka import Provider, Scope, provide

from ...application.ports.provider import ICredentialStore
from ...infra.adapters.keyring import KeyringCredentialStore


class CredentialsProvider(Provider):
    """The providers' API keys: the environment, the project's .env, and the system keyring."""

    scope = Scope.APP

    @provide
    def credentials(self) -> ICredentialStore:
        return KeyringCredentialStore()
