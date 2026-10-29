from pathlib import Path

from rich.console import Console

from i18n_ai.application.ports.locale import (
    AtomStarted,
    AttemptRejected,
    EngineRequest,
    EngineSettings,
    FileClassified,
    FileTranslated,
    ILocaleTreeScanner,
    ITranslationEngine,
    TreeRequest,
)
from i18n_ai.application.ports.provider import IProviderCatalog
from i18n_ai.di.container import build_container
from i18n_ai.di.messaging import build_mediator
from i18n_ai.domain.exports.locale import LocaleCode
from i18n_ai.domain.exports.provider import ModelSpec
from support.fakes import FakeGateway, FakeModel


async def test_an_atom_tells_its_start_and_its_retries(examples: Path) -> None:
    gateway = FakeGateway(broken_first={"app.welcome"})
    container = build_container(build_mediator(), Console(quiet=True), FakeModel(gateway))
    async with container() as request:
        scanner = await request.get(ILocaleTreeScanner)
        engine = await request.get(ITranslationEngine)
        catalog = await request.get(IProviderCatalog)
        tree = await scanner.scan(
            TreeRequest(examples / "i18next" / "locales" / "en", include=("common.json",))
        )
        model = catalog.resolve(ModelSpec("openai:fake-model"))
        engine_request = EngineRequest(
            source=tree.source,
            files=tree.files,
            targets=(LocaleCode("de"),),
            existing={},
            settings=EngineSettings(model=model, max_attempts=3),
            syntax=tree.syntax,
        )
        events = [event async for event in engine.run(engine_request)]
    await container.close()

    kinds = [type(event) for event in events if not isinstance(event, FileClassified)]
    assert kinds == [AtomStarted, AttemptRejected, FileTranslated]
    rejected = next(event for event in events if isinstance(event, AttemptRejected))
    assert (rejected.messages, rejected.attempt, rejected.attempts) == (1, 2, 3)
    assert str(rejected.job.file.name) == "common.json"
    assert rejected.job.target == LocaleCode("de")
