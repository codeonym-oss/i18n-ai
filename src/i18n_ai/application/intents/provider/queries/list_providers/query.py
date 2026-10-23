from dataclasses import dataclass

from mediary.cqrs import Query, query

from .view import ProviderView


@query
@dataclass(frozen=True)
class ListProvidersQuery(Query[tuple[ProviderView, ...]]):
    """Every provider LangChain integrates, by name, whether its package is installed, and its
    API key's variable and whether it is set."""
