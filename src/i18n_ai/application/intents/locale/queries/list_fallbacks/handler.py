from dataclasses import replace
from pathlib import PurePosixPath

from mediary.cqrs import QueryHandler, query_handler

from ......domain.exports.locale import (
    KeyPath,
    LocaleCode,
    LocaleDocument,
    LocaleSchema,
    TargetLocation,
    extract_schema,
)
from .....common import record_targets
from .....ports.locale import IFallbackRecord, ILocaleStore, ILocaleTreeScanner, MessageRef
from .query import ListFallbacksQuery
from .view import FallbacksView, FallbackView

_Place = tuple[PurePosixPath, str | None]


@query_handler
class ListFallbacksQueryHandler(QueryHandler[ListFallbacksQuery, FallbacksView]):
    """Read the record, and find each entry's message: every qualifying source file in every
    locale the tree has is a target the record may name, and the same message in the other ones is
    shown beside it."""

    def __init__(
        self, scanner: ILocaleTreeScanner, store: ILocaleStore, fallbacks: IFallbackRecord
    ) -> None:
        self._scanner = scanner
        self._store = store
        self._fallbacks = fallbacks

    async def handle(self, query: ListFallbacksQuery) -> FallbacksView:
        # The whole tree, `--include` and `--exclude` aside, in the format read, since the
        # filters may be what leaves a mixed tree with one
        tree = await self._scanner.scan(query.tree)
        if query.tree.include or query.tree.exclude:
            tree = await self._scanner.scan(
                replace(query.tree, include=(), exclude=(), format=tree.format)
            )
        recorded = await self._fallbacks.read(tree.target_directory)
        if not recorded:
            return FallbacksView(())

        # 1. The targets the record may name, by their place in it
        targets = record_targets(tree)

        # 2. Each entry's message, its source text, its current one and the other targets' ones
        schemas: dict[_Place, LocaleSchema] = {}
        documents: dict[_Place, LocaleDocument | None] = {}

        async def text(place: _Place, location: TargetLocation, path: KeyPath) -> str | None:
            if place not in documents:
                documents[place] = await self._store.read(location)
            document = documents[place]
            found = document.get(path) if document is not None else None
            return found if isinstance(found, str) else None

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
            current = await text(entry.target, location, entry.path)
            if unit is None:
                views.append(FallbackView(entry, None, None, current))
                continue
            elsewhere: list[tuple[LocaleCode, str | None]] = []
            for place, (other, code, where) in targets.items():
                if other.name == file.name and place != entry.target:
                    elsewhere.append((code, await text(place, where, entry.path)))
            views.append(
                FallbackView(
                    entry,
                    MessageRef(file.name, locale, entry.path),
                    unit.source,
                    current,
                    tuple(elsewhere),
                )
            )
        return FallbacksView(tuple(views))
