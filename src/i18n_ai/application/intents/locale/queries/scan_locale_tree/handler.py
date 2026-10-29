from mediary.cqrs import QueryHandler, query_handler

from ......domain.exports.locale import extract_schema, qualify, reusable_translations
from .....common import record_target, recorded_paths, validated_targets
from .....ports.locale import IFallbackRecord, ILocaleStore, ILocaleTreeScanner
from .query import ScanLocaleTreeQuery
from .view import ScanReport, SourceFileView, TargetFileView, TargetView


@query_handler
class ScanLocaleTreeQueryHandler(QueryHandler[ScanLocaleTreeQuery, ScanReport]):
    """Scan the tree, qualify its source files, and count what each target needs. The existing
    target files are read to tell their good translations, which are kept, from the rest; the
    recorded fallbacks are not among them, since the run translates them again."""

    def __init__(
        self, scanner: ILocaleTreeScanner, store: ILocaleStore, fallbacks: IFallbackRecord
    ) -> None:
        self._scanner = scanner
        self._store = store
        self._fallbacks = fallbacks

    async def handle(self, query: ScanLocaleTreeQuery) -> ScanReport:
        # 1. The tree, and the targets it can take
        tree = await self._scanner.scan(query.tree)
        targets = validated_targets(tree, query.targets)

        # 2. Which source files qualify
        files: list[SourceFileView] = []
        qualified = []
        for file in tree.files:
            qualification = qualify(file.document, file.error)
            files.append(
                SourceFileView(
                    name=str(file.name),
                    path=file.path,
                    qualifies=qualification.qualifies,
                    reason=qualification.reason,
                    messages=qualification.messages,
                )
            )
            if qualification.qualifies:
                qualified.append(file)

        # 3. What each target needs, file by file
        recorded = await self._fallbacks.read(tree.target_directory)
        views: list[TargetView] = []
        for target in targets:
            target_files: list[TargetFileView] = []
            for file in qualified:
                assert file.document is not None
                location = tree.target_location(target, file)
                existing = await self._store.read(location)
                if existing is not None:
                    place = record_target(tree.target_directory, location)
                    existing = existing.without(recorded_paths(recorded, place))
                schema = extract_schema(file.document, tree.source, target, tree.syntax)
                reusable = len(reusable_translations(schema, existing))
                target_files.append(
                    TargetFileView(
                        file=str(file.name),
                        path=location.path,
                        bundle_key=location.bundle_key,
                        exists=existing is not None,
                        to_translate=len(schema.units) - reusable,
                        reusable=reusable,
                    )
                )
            views.append(
                TargetView(
                    locale=target.value,
                    name=target.display_name,
                    direction=target.direction,
                    exists=tree.has(target),
                    files=tuple(target_files),
                )
            )

        return ScanReport(
            root=tree.root,
            layout=tree.layout.value,
            format=tree.format.value,
            source=tree.source.value,
            source_name=tree.source.display_name,
            source_path=tree.source_path,
            output=tree.output,
            existing=tuple(locale.value for locale in tree.existing),
            files=tuple(files),
            targets=tuple(views),
            left_alone=tuple(format.value for format in tree.left_alone),
            source_from=tree.source_from,
        )
