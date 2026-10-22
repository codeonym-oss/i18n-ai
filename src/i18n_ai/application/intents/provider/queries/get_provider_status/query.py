from dataclasses import dataclass

from mediary.cqrs import Query, query

from ......domain.exports.provider import ModelSpec
from .view import ProviderStatusView


@query
@dataclass(frozen=True)
class GetProviderStatusQuery(Query[ProviderStatusView]):
    """The provider of a model, and whether its package is installed. Raises
    `ProviderUnknown`."""

    model: ModelSpec
