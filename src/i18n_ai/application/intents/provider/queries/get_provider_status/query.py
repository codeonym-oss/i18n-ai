from dataclasses import dataclass

from mediary.cqrs import Query, query

from ......domain.exports.provider import ModelSpec
from .view import ProviderStatusView


@query
@dataclass(frozen=True)
class GetProviderStatusQuery(Query[ProviderStatusView]):
    """The provider of a model, whether its package is installed, and whether its API key is
    set. Raises `ProviderUnknown`."""

    model: ModelSpec
