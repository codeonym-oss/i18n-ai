from mediary.cqrs import QueryHandler, query_handler

from .....ports.provider import ICredentialStore, IProviderCatalog
from .query import ListProviderKeysQuery
from .view import KeysView, KeyView


@query_handler
class ListProviderKeysQueryHandler(QueryHandler[ListProviderKeysQuery, KeysView]):
    def __init__(self, providers: IProviderCatalog, credentials: ICredentialStore) -> None:
        self._providers = providers
        self._credentials = credentials

    async def handle(self, query: ListProviderKeysQuery) -> KeysView:
        providers = sorted(self._providers.providers(), key=lambda provider: provider.name)
        keys = tuple(
            KeyView(provider.name, provider.key, provider.key_source)
            for provider in providers
            if provider.key is not None
        )
        return KeysView(self._credentials.keyring(), keys)
