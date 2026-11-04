from dataclasses import replace
from pathlib import PurePosixPath

from mediary.cqrs import CommandHandler, command_handler

from ......domain.exports.locale import KeyPath, LocaleDocument, qualify
from ......domain.exports.provider import ProviderNotInstalled
from .....common import WRITTEN, record_target, recorded_fallbacks, settle, validated_targets
from .....ports.locale import (
    EngineRequest,
    EngineSettings,
    FileFailed,
    FileTranslated,
    IFallbackRecord,
    ILocaleStore,
    ILocaleTreeScanner,
    ITranslationEngine,
    RecordedFallback,
)
from .....ports.progress import FileResult
from .....ports.provider import IProviderCatalog
from ..generate_locales import GenerationReceipt
from .cmd import RetryFallbacksCommand

_Pair = tuple[PurePosixPath, str]
_Place = tuple[PurePosixPath, str | None]


@command_handler
class RetryFallbacksCommandHandler(CommandHandler[RetryFallbacksCommand, GenerationReceipt]):
    """Give the engine each chosen message's file and target, with the target's document
    without the chosen messages: the engine translates those, and reuses the rest."""

    def __init__(
        self,
        scanner: ILocaleTreeScanner,
        store: ILocaleStore,
        engine: ITranslationEngine,
        providers: IProviderCatalog,
        fallbacks: IFallbackRecord,
    ) -> None:
        self._scanner = scanner
        self._store = store
        self._engine = engine
        self._providers = providers
        self._fallbacks = fallbacks

    async def handle(self, command: RetryFallbacksCommand) -> GenerationReceipt:
        options = command.options

        # 1. The model, whose provider must be installed
        model = self._providers.resolve(command.model)
        if not self._providers.is_installed(model.module):
            raise ProviderNotInstalled(model.provider, model.package)

        # 2. The chosen messages, by file and target, but for those whose file is gone
        tree = await self._scanner.scan(replace(command.tree, include=(), exclude=()))
        targets = validated_targets(tree, (message.target for message in command.messages))
        sources = {
            file.name: file for file in tree.files if qualify(file.document, file.error).qualifies
        }
        chosen: dict[_Pair, list[KeyPath]] = {}
        for message in command.messages:
            if message.file in sources:
                chosen.setdefault((message.file, message.target.key), []).append(message.path)
        files = [sources[name] for name in dict.fromkeys(name for name, _ in chosen)]
        keys = {key for _, key in chosen}
        targets = tuple(target for target in targets if target.key in keys)
        skip = frozenset(
            (file.name, target.key)
            for file in files
            for target in targets
            if (file.name, target.key) not in chosen
        )

        # 3. Each target's document, without the chosen messages
        directory = tree.target_directory
        existing: dict[_Pair, LocaleDocument] = {}
        places: dict[_Pair, _Place] = {}
        for file in files:
            for target in targets:
                pair = (file.name, target.key)
                if pair in chosen:
                    location = tree.target_location(target, file)
                    places[pair] = record_target(directory, location)
                    document = await self._store.read(location)
                    if document is not None:
                        existing[pair] = document.without(chosen[pair])

        # 4. The engine, writing each file as it is translated
        request = EngineRequest(
            source=tree.source,
            files=tuple(files),
            targets=targets,
            existing=existing,
            settings=EngineSettings(
                model=model,
                batch_size=options.batch_size,
                concurrency=options.concurrency,
                max_attempts=options.max_attempts,
                classify=False,
                context=options.context,
                temperature=options.temperature,
            ),
            syntax=tree.syntax,
            skip=skip,
        )
        recorded = await self._fallbacks.read(directory)
        results: list[FileResult] = []
        retried: dict[_Place, set[KeyPath]] = {}
        entries: list[RecordedFallback] = []
        try:
            async for event in self._engine.run(request):
                if not isinstance(event, FileTranslated | FileFailed):
                    continue
                result = await settle(self._store, tree, event, options.strict)
                results.append(result)
                if isinstance(event, FileTranslated) and result.status in WRITTEN:
                    pair = (event.job.file.name, event.job.target.key)
                    place = places[pair]
                    retried[place] = {*chosen[pair], *event.rejected}
                    entries.extend(recorded_fallbacks(place, event))
        finally:
            # The chosen entries leave the record, and those that failed again come back
            if retried:
                kept = [
                    entry
                    for entry in recorded
                    if entry.path not in retried.get(entry.target, set())
                ]
                await self._fallbacks.write(directory, tuple(kept + entries))

        return GenerationReceipt(model=model.spec, results=tuple(results))
