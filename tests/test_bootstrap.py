from pathlib import Path

import pytest
from mediary import Mediator
from rich.console import Console

from i18n_ai.application.exports.locale import GenerateLocalesCommand
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
        self.seen: list[str] = []

    def start(self, jobs: int) -> None:
        self.seen.append(f"start {jobs}")

    def drop(self, jobs: int, reason: str) -> None:
        self.seen.append(f"drop {jobs}")

    def advance(self, description: str) -> None:
        self.seen.append("advance")

    def finish(self) -> None:
        self.seen.append("finish")


@pytest.fixture(autouse=True)
def fake_model(monkeypatch: pytest.MonkeyPatch) -> None:
    """The fake model before the overrides, whose progress then wins over the fake's."""
    build = bootstrap.build_container
    monkeypatch.setattr(
        bootstrap,
        "build_container",
        lambda mediator, console, *overrides: build(
            mediator, console, FakeModel(FakeGateway()), *overrides
        ),
    )


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

    assert progress.seen[0].startswith("start ")
    assert "advance" in progress.seen
    assert progress.seen[-1] == "finish"
