from mediary.cqrs import QueryHandler, query_handler

from ......domain.exports.locale import known_locales
from .query import ListLocalesQuery
from .view import LocaleView


@query_handler
class ListLocalesQueryHandler(QueryHandler[ListLocalesQuery, tuple[LocaleView, ...]]):
    async def handle(self, query: ListLocalesQuery) -> tuple[LocaleView, ...]:
        return tuple(
            LocaleView(locale.value, locale.display_name, locale.direction)
            for locale in known_locales()
        )
