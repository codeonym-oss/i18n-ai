from dataclasses import replace
from pathlib import PurePosixPath

from mediary.cqrs import QueryHandler, query_handler

from ......domain.exports.locale import (
    LocaleCode,
    LocaleSchema,
    SourceFile,
    TargetLocation,
    extract_schema,
    qualify,
)
from .....common import record_target
from .....ports.locale import IFallbackRecord, ILocaleStore, ILocaleTreeScanner, MessageRef
from .query import ListFallbacksQuery
from .view import FallbacksView, FallbackView

_Place = tuple[PurePosixPath, str | None]


@query_handler
class ListFallbacksQueryHandler(QueryHandler[ListFallbacksQuery, FallbacksView]):
    """Read the record, and find each entry's message: every qualifying source file in every
    locale the tree has is a target the record may name."""

    def __init__(
        self, scanner: ILocaleTreeScanner, store: ILocaleStore, fallbacks: IFallbackRecord
    ) -> None:
        self._scanner = scanner
        self._store = store
        self._fallbacks = fallbacks

    async def handle(self, query: ListFallbacksQuery) -> FallbacksView:
        tree = await self._scanner.scan(replace(query.tree, include=(), exclude=()))
        recorded = await self._fallbacks.read(tree.target_directory)
        if not recorded:
            return FallbacksView(())

        # 1. The targets the record may name, by their place in it
        targets: dict[_Place, tuple[SourceFile, LocaleCode, TargetLocation]] = {}
        for file in tree.files:
            if not qualify(file.document, file.error).qualifies:
                continue
            for locale in tree.existing:
                if not locale.same_as(tree.source):
                    location = tree.target_location(locale, file)
                    targets[record_target(tree.target_directory, location)] = (
                        file,
                        locale,
                        location,
                    )

        # 2. Each entry's message, its source text and its current one
        schemas: dict[_Place, LocaleSchema] = {}
        views: list[FallbackView] = []
        for entry in recorded:
            found = targets.get(entry.target)
            if found is None:
                views.append(FallbackView(entry, None, None, None))
                continue
            file, locale, location = found
            if entry.target not in schemas:
                assert file.document is not None
                schemas[entry.target] = extract_schema(
                    file.document, tree.source, locale, tree.syntax
                )
            unit = next((u for u in schemas[entry.target].units if u.path == entry.path), None)
            document = await self._store.read(location)
            current = document.get(entry.path) if document is not None else None
            views.append(
                FallbackView(
                    entry,
                    MessageRef(file.name, locale, entry.path) if unit is not None else None,
                    unit.source if unit is not None else None,
                    current if isinstance(current, str) else None,
                )
            )
        return FallbacksView(tuple(views))
