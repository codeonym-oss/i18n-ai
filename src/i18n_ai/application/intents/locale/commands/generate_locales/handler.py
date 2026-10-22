import logging
from pathlib import PurePosixPath

from mediary.cqrs import CommandHandler, command_handler

from ......domain.exports.locale import LocaleDocument, LocaleTree, SourceFile, qualify
from ......domain.exports.provider import ProviderNotInstalled
from .....common.targets import validated_targets
from .....ports.locale import (
    EngineRequest,
    EngineSettings,
    FileClassified,
    FileFailed,
    FileTranslated,
    ILocaleStore,
    ILocaleTreeScanner,
    ITranslationEngine,
)
from .....ports.progress import IGenerationProgress
from .....ports.provider import IProviderCatalog
from .cmd import GenerateLocalesCommand
from .receipt import FileResult, GenerationReceipt, ResultStatus

logger = logging.getLogger(__name__)


@command_handler
class GenerateLocalesCommandHandler(CommandHandler[GenerateLocalesCommand, GenerationReceipt]):
    """Generate the targets: the files that qualify go to the engine, and each translation is
    written as soon as it comes back, so a long run keeps what it has done."""

    def __init__(
        self,
        scanner: ILocaleTreeScanner,
        store: ILocaleStore,
        engine: ITranslationEngine,
        providers: IProviderCatalog,
        progress: IGenerationProgress,
    ) -> None:
        self._scanner = scanner
        self._store = store
        self._engine = engine
        self._providers = providers
        self._progress = progress

    async def handle(self, command: GenerateLocalesCommand) -> GenerationReceipt:
        options = command.options

        # 1. The model, whose provider must be installed
        model = self._providers.resolve(command.model)
        if not self._providers.is_installed(model.module):
            raise ProviderNotInstalled(model.provider, model.package)

        # 2. The tree, its targets, and the files that qualify
        tree = await self._scanner.scan(command.tree)
        targets = validated_targets(tree, command.targets)
        results: list[FileResult] = []
        qualified: list[SourceFile] = []
        for file in tree.files:
            qualification = qualify(file.document, file.error)
            if qualification.qualifies:
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

        # 3. The existing targets, whose good translations are kept
        existing: dict[tuple[PurePosixPath, str], LocaleDocument] = {}
        if not options.overwrite:
            for file in qualified:
                for target in targets:
                    document = await self._store.read(tree.target_location(target, file))
                    if document is not None:
                        existing[(file.name, target.key)] = document

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
        )
        self._progress.start(len(qualified) * len(targets))
        try:
            async for event in self._engine.run(request):
                if isinstance(event, FileClassified):
                    if not event.qualifies:
                        self._progress.drop(len(targets), f"{event.file.name}: {event.reason}")
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
                self._progress.advance(f"{result.file} → {result.target}: {result.status.value}")
        finally:
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
            assert job.file.document is not None
            await self._store.write(location, event.content, job.file.document.style)
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
