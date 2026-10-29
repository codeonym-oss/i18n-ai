import logging
from pathlib import PurePosixPath

from mediary.cqrs import CommandHandler, command_handler

from ......domain.exports.locale import (
    LocaleCode,
    LocaleDocument,
    LocaleTree,
    SourceFile,
    qualify,
)
from ......domain.exports.provider import ProviderNotInstalled
from .....common import record_target, recorded_paths, validated_targets
from .....ports.locale import (
    EngineRequest,
    EngineSettings,
    FallbackProblem,
    FileClassified,
    FileFailed,
    FileTranslated,
    IFallbackRecord,
    ILocaleStore,
    ILocaleTreeScanner,
    ITranslationEngine,
    RecordedFallback,
)
from .....ports.progress import IGenerationProgress
from .....ports.provider import IProviderCatalog
from .cmd import GenerateLocalesCommand
from .receipt import FileResult, GenerationReceipt, ResultStatus

logger = logging.getLogger(__name__)


@command_handler
class GenerateLocalesCommandHandler(CommandHandler[GenerateLocalesCommand, GenerationReceipt]):
    """Generate the targets: the files that qualify go to the engine, and each translation is
    written as soon as it comes back, so a long run keeps what it has done. The fallbacks are
    recorded beside the targets, and the next run translates them again."""

    def __init__(
        self,
        scanner: ILocaleTreeScanner,
        store: ILocaleStore,
        engine: ITranslationEngine,
        providers: IProviderCatalog,
        progress: IGenerationProgress,
        fallbacks: IFallbackRecord,
    ) -> None:
        self._scanner = scanner
        self._store = store
        self._engine = engine
        self._providers = providers
        self._progress = progress
        self._fallbacks = fallbacks

    async def handle(self, command: GenerateLocalesCommand) -> GenerationReceipt:
        options = command.options

        # 1. The model, whose provider must be installed
        model = self._providers.resolve(command.model)
        if not self._providers.is_installed(model.module):
            raise ProviderNotInstalled(model.provider, model.package)

        # 2. The tree, its targets, and the files that qualify, but for those every target skips
        tree = await self._scanner.scan(command.tree)
        targets = validated_targets(tree, command.targets)
        skip = frozenset((file, target.key) for file, target in command.skip)

        def wanted(file: SourceFile) -> list[LocaleCode]:
            return [target for target in targets if (file.name, target.key) not in skip]

        results: list[FileResult] = []
        qualified: list[SourceFile] = []
        for file in tree.files:
            qualification = qualify(file.document, file.error)
            if qualification.qualifies:
                if wanted(file):
                    qualified.append(file)
            else:
                results.append(
                    FileResult(
                        str(file.name),
                        None,
                        file.path,
                        ResultStatus.IGNORED,
                        reason=qualification.reason,
                    )
                )

        # 3. The existing targets, whose good translations are kept, but for the recorded fallbacks
        directory = tree.target_directory
        recorded = await self._fallbacks.read(directory)
        existing: dict[tuple[PurePosixPath, str], LocaleDocument] = {}
        if not options.overwrite:
            for file in qualified:
                for target in wanted(file):
                    location = tree.target_location(target, file)
                    document = await self._store.read(location)
                    if document is not None:
                        place = record_target(directory, location)
                        existing[(file.name, target.key)] = document.without(
                            recorded_paths(recorded, place)
                        )

        # 4. The engine, writing each file as it is translated
        request = EngineRequest(
            source=tree.source,
            files=tuple(qualified),
            targets=targets,
            existing=existing,
            settings=EngineSettings(
                model=model,
                batch_size=options.batch_size,
                concurrency=options.concurrency,
                max_attempts=options.max_attempts,
                classify=options.classify,
                context=options.context,
                temperature=options.temperature,
            ),
            syntax=tree.syntax,
            skip=skip,
        )
        self._progress.start(sum(len(wanted(file)) for file in qualified))
        written: set[tuple[PurePosixPath, str | None]] = set()
        entries: list[RecordedFallback] = []
        try:
            async for event in self._engine.run(request):
                if isinstance(event, FileClassified):
                    if not event.qualifies:
                        self._progress.drop(
                            len(wanted(event.file)), f"{event.file.name}: {event.reason}"
                        )
                        results.append(
                            FileResult(
                                str(event.file.name),
                                None,
                                event.file.path,
                                ResultStatus.IGNORED,
                                reason=event.reason,
                            )
                        )
                    continue
                result = await self._settle(tree, event, options.strict)
                results.append(result)
                if isinstance(event, FileTranslated) and result.status in _WRITTEN:
                    location = tree.target_location(event.job.target, event.job.file)
                    place = record_target(directory, location)
                    written.add(place)
                    entries.extend(_recorded(place, event))
                self._progress.advance(f"{result.file} → {result.target}: {result.status.value}")
        finally:
            if written:
                kept = [entry for entry in recorded if entry.target not in written]
                await self._fallbacks.write(directory, tuple(kept + entries))
            self._progress.finish()

        return GenerationReceipt(model=model.spec, results=tuple(results))

    async def _settle(
        self, tree: LocaleTree, event: FileTranslated | FileFailed, strict: bool
    ) -> FileResult:
        """Write a translated file, unless it is refused; and say what became of it."""
        job = event.job
        location = tree.target_location(job.target, job.file)
        name, target = str(job.file.name), job.target.value
        if isinstance(event, FileFailed):
            logger.warning("%s → %s failed: %s", name, target, event.error)
            return FileResult(name, target, location.path, ResultStatus.FAILED, reason=event.error)

        status = ResultStatus.PARTIAL if event.failures else ResultStatus.WRITTEN
        if event.failures and strict:
            status = ResultStatus.REFUSED
        else:
            await self._store.write(location, event.content, job.file)
        return FileResult(
            file=name,
            target=target,
            path=location.path,
            status=status,
            translated=event.translated,
            reused=event.reused,
            failures=event.failures,
            warnings=event.warnings,
        )


_WRITTEN = (ResultStatus.WRITTEN, ResultStatus.PARTIAL)


def _recorded(
    place: tuple[PurePosixPath, str | None], event: FileTranslated
) -> list[RecordedFallback]:
    """The fallbacks `event` wrote at `place`, as the record keeps them."""
    file, key = place
    return [
        RecordedFallback(
            file,
            key,
            path,
            tuple(
                FallbackProblem(violation.code, violation.message)
                for violation in event.failures
                if violation.path == path
            ),
            rejected,
        )
        for path, rejected in event.rejected.items()
    ]
