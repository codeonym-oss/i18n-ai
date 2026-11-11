"""The TUI driven with Textual's pilot: the app, waiting on it, and the setup filled in."""

import time
from collections.abc import Awaitable, Callable
from pathlib import Path

from mediary import Mediator
from rich.console import Console
from textual.pilot import Pilot
from textual.widgets import Input, Select

from i18n_ai.application.exports.locale import GenerateLocalesCommand, GenerationOptions
from i18n_ai.application.ports.locale import TreeRequest
from i18n_ai.cli.tui import I18nAiApp
from i18n_ai.cli.tui.kit.widgets import LocaleCard
from i18n_ai.cli.tui.plan import PlanScreen
from i18n_ai.cli.tui.run import RunScreen
from i18n_ai.di.container import build_container
from i18n_ai.di.messaging import build_mediator
from i18n_ai.domain.exports.locale import LocaleCode
from i18n_ai.domain.exports.provider import ModelSpec
from i18n_ai.runtime.config import GenerationConfig
from i18n_ai.runtime.settings import Settings
from support.fakes import FakeGateway, FakeModel

# The snapshot fixture: an app, its size, and what to do before the picture
type Snap = Callable[..., Awaitable[None]]


def tui(project: Path, model: str | None = None, attempts: int = 3) -> I18nAiApp:
    settings = Settings(generation=GenerationConfig(model=model, max_attempts=attempts))
    return I18nAiApp(settings, project)


async def settle(pilot: Pilot[None]) -> None:
    """Until no worker is running and the messages are handled."""
    await pilot.pause()
    await pilot.app.workers.wait_for_complete()
    await pilot.pause()


async def pick(pilot: Pilot[None], selector: str, value: str) -> None:
    pilot.app.screen.query_one(selector, Select).value = value
    await settle(pilot)


async def ended(pilot: Pilot[None], seconds: float = 10) -> RunScreen:
    """The run screen, once the run is over."""
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        screen = pilot.app.screen
        if isinstance(screen, RunScreen) and screen.done:
            return screen
        await pilot.pause(0.05)
    raise AssertionError(f"the run did not end (on {type(pilot.app.screen).__name__})")


async def planning(pilot: Pilot[None], seconds: float = 10) -> PlanScreen:
    """The plan screen, from the setup's Plan; the setup's worker waits on it, so it is polled
    for, not settled."""
    await pilot.press("ctrl+r")
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        screen = pilot.app.screen
        if isinstance(screen, PlanScreen) and screen.is_mounted:
            await pilot.pause()
            return screen
        await pilot.pause(0.05)
    raise AssertionError(f"no plan (on {type(pilot.app.screen).__name__})")


async def pick_targets(pilot: Pilot[None], *codes: str) -> None:
    """Each of `codes` toggled on its card, searched for first, as a person would."""
    search = pilot.app.screen.query_one("#search", Input)
    for code in codes:
        search.value = code
        await settle(pilot)
        card = next(card for card in pilot.app.screen.query(LocaleCard) if card.code == code)
        card.action_pick()
        await settle(pilot)
    search.value = ""
    await settle(pilot)


async def ready(pilot: Pilot[None], *targets: str) -> None:
    """The setup filled in, with `targets` picked as well."""
    screen = pilot.app.screen
    await pick_targets(pilot, *targets)
    await pick(pilot, "#provider", "openai")
    screen.query_one("#key", Input).value = "sk-test"
    await pick(pilot, "#model", "fake-model")


async def running(pilot: Pilot[None]) -> None:
    """The Run section's setup, from Home where the app opens."""
    await settle(pilot)
    await pilot.press("ctrl+n")
    await settle(pilot)


async def fallen(project: Path, gateway: FakeGateway, *keys: str) -> None:
    """A CLI run into fr that leaves `keys` as fallbacks, as `i18n-ai generate` would."""
    gateway.broken_first = set(keys)
    container = build_container(build_mediator(), Console(quiet=True), FakeModel(gateway))
    async with container() as request:
        mediator = await request.get(Mediator)
        await mediator.send(
            GenerateLocalesCommand(
                TreeRequest(project / "locales" / "en"),
                (LocaleCode("fr"),),
                ModelSpec("openai:fake-model"),
                GenerationOptions(max_attempts=1),
            )
        )
    await container.close()
    gateway.broken_first = set()
    gateway.batches.clear()
