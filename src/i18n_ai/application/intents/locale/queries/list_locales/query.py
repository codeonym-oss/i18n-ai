from dataclasses import dataclass

from mediary.cqrs import Query, query

from .view import LocaleView


@query
@dataclass(frozen=True)
class ListLocalesQuery(Query[tuple[LocaleView, ...]]):
    """The locales to pick targets from, from CLDR: the ones websites ship most first, then
    every language by name."""
