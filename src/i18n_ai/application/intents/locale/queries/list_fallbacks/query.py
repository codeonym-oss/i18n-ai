from dataclasses import dataclass

from mediary.cqrs import Query, query

from .....ports.locale import TreeRequest
from .view import FallbacksView


@query
@dataclass(frozen=True)
class ListFallbacksQuery(Query[FallbacksView]):
    """The fallbacks recorded beside a tree's targets, each with its source text and its current
    one. The tree's `include` and `exclude` are not applied: a file left out of a run still has
    its fallbacks. Raises `LocaleTreeNotFound`, `SourceLocaleUnknown` or `MixedLocaleFormats`."""

    tree: TreeRequest
