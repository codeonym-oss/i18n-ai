from mediary.cqrs import QueryHandler, query_handler

from ......domain.exports.locale import LocaleCode
from .....ports.locale import ILocaleTreeScanner
from .query import DetectLocaleTreesQuery
from .view import TreeCandidateView

_DEFAULT_SOURCE = LocaleCode("en")


@query_handler
class DetectLocaleTreesQueryHandler(
    QueryHandler[DetectLocaleTreesQuery, tuple[TreeCandidateView, ...]]
):
    def __init__(self, scanner: ILocaleTreeScanner) -> None:
        self._scanner = scanner

    async def handle(self, query: DetectLocaleTreesQuery) -> tuple[TreeCandidateView, ...]:
        views = []
        for candidate in await self._scanner.detect(query.root):
            source = next(
                (locale for locale in candidate.locales if locale.same_as(_DEFAULT_SOURCE)),
                candidate.locales[0] if len(candidate.locales) == 1 else None,
            )
            views.append(
                TreeCandidateView(
                    path=candidate.path,
                    layout=candidate.layout.value,
                    locales=tuple(locale.value for locale in candidate.locales),
                    source=source.value if source is not None else None,
                    formats=tuple(format.value for format in candidate.formats),
                )
            )
        return tuple(views)
