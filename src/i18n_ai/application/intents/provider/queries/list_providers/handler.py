from mediary.cqrs import QueryHandler, query_handler

from .....ports.provider import IProviderCatalog
from .query import ListProvidersQuery
from .view import ProviderView


@query_handler
class ListProvidersQueryHandler(QueryHandler[ListProvidersQuery, tuple[ProviderView, ...]]):
    def __init__(self, providers: IProviderCatalog) -> None:
        self._providers = providers

    async def handle(self, query: ListProvidersQuery) -> tuple[ProviderView, ...]:
        providers = sorted(self._providers.providers(), key=lambda provider: provider.name)
        return tuple(
            ProviderView(provider.name, provider.package, provider.installed)
            for provider in providers
        )
