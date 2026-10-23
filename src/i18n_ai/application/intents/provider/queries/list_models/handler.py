from mediary.cqrs import QueryHandler, query_handler

from .....ports.provider import IModelLister, IProviderCatalog, ModelInfo
from .query import ListModelsQuery
from .view import ModelsView, ModelView


@query_handler
class ListModelsQueryHandler(QueryHandler[ListModelsQuery, ModelsView]):
    def __init__(self, providers: IProviderCatalog, models: IModelLister) -> None:
        self._providers = providers
        self._models = models

    async def handle(self, query: ListModelsQuery) -> ModelsView:
        provider = self._providers.provider(query.provider)
        listing = await self._models.models(provider.name)
        models = sorted(listing.models, key=_order)
        return ModelsView(
            provider=provider.name,
            models=tuple(
                ModelView(model.id, model.rank is not None, model.created) for model in models
            ),
            live=listing.live,
            problem=listing.problem,
        )


def _order(model: ModelInfo) -> tuple[int, float, str]:
    """The recommended first, in their order; then the newest; then by name."""
    if model.rank is not None:
        return (0, model.rank, model.id)
    return (1, -(model.created or 0), model.id)
