import logging
from collections import Counter
from dataclasses import replace
from pathlib import PurePosixPath

from mediary.cqrs import CommandHandler, command_handler

from ......domain.exports.locale import (
    LocaleCode,
    LocaleDocument,
    SourceFile,
    qualify,
)
from ......domain.exports.provider import ProviderNotInstalled
from .....common import (
    WRITTEN,
    record_target,
    record_targets,
    recorded_fallbacks,
    recorded_paths,
    settle,
    validated_targets,
)
from .....ports.locale import (
    AtomStarted,
    AttemptRejected,
    EngineRequest,
    EngineSettings,
    FileClassified,
    FileTranslated,
    IFallbackRecord,
    ILocaleStore,
    ILocaleTreeScanner,
    ITranslationEngine,
    RecordedFallback,
)
from .....ports.progress import (
    FileDropped,
    FileResult,
    IGenerationProgress,
    JobDone,
    JobRetrying,
    JobStarted,
    ResultStatus,
    RunFinished,
    RunStarted,
)
from .....ports.provider import IProviderCatalog
from .cmd import GenerateLocalesCommand
from .receipt import GenerationReceipt

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
        # The whole tree, `--include` and `--exclude` aside, tells which entries have no target;
        # in the format read, since the filters may be what leaves a mixed tree with one
        whole = tree
        if command.tree.include or command.tree.exclude:
            whole = await self._scanner.scan(
                replace(command.tree, include=(), exclude=(), format=tree.format)
            )
        places = record_targets(whole)
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
        self._progress.on(RunStarted(sum(len(wanted(file)) for file in qualified)))
        written: set[tuple[PurePosixPath, str | None]] = set()
        entries: list[RecordedFallback] = []
        try:
            async for event in self._engine.run(request):
                if isinstance(event, FileClassified):
                    if not event.qualifies:
                        self._progress.on(
                            FileDropped(str(event.file.name), len(wanted(event.file)), event.reason)
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
                if isinstance(event, AtomStarted):
                    job = event.job
                    self._progress.on(JobStarted(str(job.file.name), job.target.value))
                    continue
                if isinstance(event, AttemptRejected):
                    job = event.job
                    self._progress.on(
                        JobRetrying(
                            str(job.file.name),
                            job.target.value,
                            event.messages,
                            event.attempt,
                            event.attempts,
                        )
                    )
                    continue
                result = await settle(self._store, tree, event, options.strict)
                results.append(result)
                if isinstance(event, FileTranslated) and result.status in WRITTEN:
                    location = tree.target_location(event.job.target, event.job.file)
                    place = record_target(directory, location)
                    written.add(place)
                    entries.extend(recorded_fallbacks(place, event))
                self._progress.on(JobDone(result))
        finally:
            gone = [entry for entry in recorded if entry.target not in places]
            if gone:
                logger.info(
                    "dropped %d fallback record entries with no target: %s",
                    len(gone),
                    ", ".join(sorted({str(entry.file) for entry in gone})),
                )
            kept = [
                entry
                for entry in recorded
                if entry.target in places and entry.target not in written
            ]
            if Counter(kept + entries) != Counter(recorded):
                await self._fallbacks.write(directory, tuple(kept + entries))
            self._progress.on(RunFinished())

        return GenerationReceipt(model=model.spec, results=tuple(results))
