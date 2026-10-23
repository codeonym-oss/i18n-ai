from dataclasses import dataclass

from mediary.cqrs import Query, query

from .view import ModelsView


@query
@dataclass(frozen=True)
class ListModelsQuery(Query[ModelsView]):
    """The models of a provider, from its API when it can be reached. Raises `ProviderUnknown`."""

    provider: str
