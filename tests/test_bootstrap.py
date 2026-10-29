from pathlib import Path, PurePosixPath

import pytest
from mediary import Mediator
from rich.console import Console

from i18n_ai.application.exports.locale import (
    GenerateLocalesCommand,
    JobDone,
    JobRetrying,
    JobStarted,
    ProgressEvent,
    RunFinished,
    RunStarted,
)
from i18n_ai.application.ports.locale import TreeRequest
from i18n_ai.application.ports.progress import IGenerationProgress
from i18n_ai.di import Bootstrap, bootstrap
from i18n_ai.domain.exports.locale import LocaleCode
from i18n_ai.domain.exports.provider import ModelSpec
from i18n_ai.runtime.config import GenerationConfig
from i18n_ai.runtime.settings import Settings
from support.fakes import FakeGateway, FakeModel


class RecordingProgress(IGenerationProgress):
    def __init__(self) -> None:
        self.seen: list[ProgressEvent] = []

    def on(self, event: ProgressEvent) -> None:
        self.seen.append(event)


@pytest.fixture(autouse=True)
def fake_model(monkeypatch: pytest.MonkeyPatch) -> FakeGateway:
    """The fake model before the overrides, whose progress then wins over the fake's."""
    gateway = FakeGateway()
    build = bootstrap.build_container
    monkeypatch.setattr(
        bootstrap,
        "build_container",
        lambda mediator, console, *overrides: build(
            mediator, console, FakeModel(gateway), *overrides
        ),
    )
    return gateway


async def generate(mediator: Mediator, examples: Path) -> None:
    tree = TreeRequest(examples / "i18next" / "locales" / "en")
    await mediator.send(
        GenerateLocalesCommand(tree, (LocaleCode("fr"),), ModelSpec("openai:fake-model"))
    )


async def test_a_run_shows_on_the_progress_it_is_given(examples: Path) -> None:
    progress = RecordingProgress()
    settings = Settings(generation=GenerationConfig())

    async with Bootstrap(settings, Console(quiet=True), progress=progress) as app:
        await generate(app.mediator, examples)

    assert progress.seen[0] == RunStarted(2)
    assert JobStarted("common.json", "fr") in progress.seen
    assert sum(isinstance(event, JobDone) for event in progress.seen) == 2
    assert progress.seen[-1] == RunFinished()


async def test_the_progress_counts_the_jobs_a_skip_leaves(examples: Path) -> None:
    progress = RecordingProgress()
    settings = Settings(generation=GenerationConfig())
    tree = TreeRequest(examples / "i18next" / "locales" / "en")
    skip = frozenset({(PurePosixPath("common.json"), LocaleCode("de"))})

    async with Bootstrap(settings, Console(quiet=True), progress=progress) as app:
        await app.mediator.send(
            GenerateLocalesCommand(
                tree,
                (LocaleCode("fr"), LocaleCode("de")),
                ModelSpec("openai:fake-model"),
                skip=skip,
            )
        )

    assert progress.seen[0] == RunStarted(3)
    assert sum(isinstance(event, JobDone) for event in progress.seen) == 3


async def test_a_retry_shows_as_it_happens(fake_model: FakeGateway, examples: Path) -> None:
    fake_model.broken_first = {"app.welcome"}
    progress = RecordingProgress()

    async with Bootstrap(
        Settings(generation=GenerationConfig()), Console(quiet=True), progress
    ) as app:
        await generate(app.mediator, examples)

    assert JobRetrying("common.json", "fr", 1, 2, 3) in progress.seen
