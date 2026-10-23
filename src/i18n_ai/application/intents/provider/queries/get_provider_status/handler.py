from mediary.cqrs import QueryHandler, query_handler

from .....ports.provider import IProviderCatalog
from .query import GetProviderStatusQuery
from .view import ProviderStatusView


@query_handler
class GetProviderStatusQueryHandler(QueryHandler[GetProviderStatusQuery, ProviderStatusView]):
    def __init__(self, providers: IProviderCatalog) -> None:
        self._providers = providers

    async def handle(self, query: GetProviderStatusQuery) -> ProviderStatusView:
        model = self._providers.resolve(query.model)
        provider = self._providers.provider(model.provider)
        return ProviderStatusView(
            provider=model.provider,
            model=model.model,
            package=model.package,
            installed=self._providers.is_installed(model.module),
            key=provider.key,
            key_set=provider.key_set,
        )
