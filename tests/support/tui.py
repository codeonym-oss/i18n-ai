"""The TUI driven with Textual's pilot: the app, waiting on it, and the setup filled in."""

import time
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from mediary import Mediator
from rich.console import Console
from textual.pilot import Pilot
from textual.screen import Screen
from textual.widgets import Input, Select

from i18n_ai.application.exports.locale import (
    GenerateLocalesCommand,
    GenerationOptions,
    ProgressEvent,
    ScanLocaleTreeQuery,
)
from i18n_ai.application.ports.locale import TreeRequest
from i18n_ai.cli.common.setup import planned
from i18n_ai.cli.tui import I18nAiApp
from i18n_ai.cli.tui.kit.widgets import LocaleCard, PlanCell
from i18n_ai.cli.tui.plan import PlanScreen
from i18n_ai.cli.tui.progress import TuiProgress
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


def _widgets(pilot: Pilot[None]) -> tuple[int, ...] | None:
    """The screen's widgets, None while one of them is not yet mounted (its children not yet
    composed)."""
    widgets = list(pilot.app.screen.walk_children(with_self=True))
    if not all(widget.is_mounted for widget in widgets):
        return None
    return tuple(id(widget) for widget in widgets)


async def drawn(pilot: Pilot[None], seconds: float = 10) -> None:
    """Until the screen is drawn: every widget on it mounted, and a round of its messages that
    mounts or removes none. A slow machine composes a widget's children well after the widget
    is in the screen, and a handler rebuilds a list after the message that asked for it."""
    deadline = time.monotonic() + seconds
    before = None
    while time.monotonic() < deadline:
        await pilot.pause()
        now = _widgets(pilot)
        if now is not None and now == before:
            return
        before = now
    raise AssertionError(f"{type(pilot.app.screen).__name__} is still drawing")


async def settle(pilot: Pilot[None]) -> None:
    """Until no worker is running and the screen is drawn."""
    while True:
        await pilot.pause()
        await pilot.app.workers.wait_for_complete()
        await drawn(pilot)
        if all(worker.is_finished for worker in pilot.app.workers):
            return


async def arrived[S: Screen[Any]](pilot: Pilot[None], kind: type[S], seconds: float = 10) -> S:
    """The screen on top once it is a `kind` and drawn; for a screen a worker waits on, which
    `settle` would wait for too."""
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        screen = pilot.app.screen
        if isinstance(screen, kind) and screen.is_mounted:
            await drawn(pilot)
            return screen
        await pilot.pause(0.05)
    raise AssertionError(f"no {kind.__name__} (on {type(pilot.app.screen).__name__})")


async def pick(pilot: Pilot[None], selector: str, value: str) -> None:
    pilot.app.screen.query_one(selector, Select).value = value
    await settle(pilot)


async def on_cell(pilot: Pilot[None], plan: PlanScreen, row: int, column: int, key: str) -> None:
    """`key` pressed on the plan's cell of the `row`th file and the `column`th locale."""
    cell = list(plan.query(PlanCell))[row * len(plan.query(".column-head")) + column]
    cell.focus()
    await pilot.press(key)
    await pilot.pause()


async def scripted(
    pilot: Pilot[None], *targets: str, off: set[tuple[str, str]] | None = None
) -> tuple[RunScreen, list[float]]:
    """A run screen pushed on its own, on the example's scan into `targets`, with no run behind
    it: the test posts its events with `post`. Its clock reads the list's last time."""
    app = pilot.app
    assert isinstance(app, I18nAiApp)
    codes = tuple(LocaleCode(code) for code in targets)
    report = await app.mediator.send(
        ScanLocaleTreeQuery(TreeRequest(app.project / "locales" / "en"), codes)
    )
    files = [file.name for file in report.qualified]
    times = [0.0]
    run = RunScreen(
        report, planned(files, codes, off or set()), "i18next/locales", lambda: times[-1]
    )
    await app.push_screen(run)
    await drawn(pilot)
    return run, times


async def post(pilot: Pilot[None], run: RunScreen, *events: ProgressEvent) -> None:
    for event in events:
        run.post_message(TuiProgress.Event(event))
    await drawn(pilot)


async def ended(pilot: Pilot[None], seconds: float = 10) -> RunScreen:
    """The run screen, once the run is over."""
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        screen = pilot.app.screen
        if isinstance(screen, RunScreen) and screen.done:
            await drawn(pilot)
            return screen
        await pilot.pause(0.05)
    raise AssertionError(f"the run did not end (on {type(pilot.app.screen).__name__})")


async def planning(pilot: Pilot[None], seconds: float = 10) -> PlanScreen:
    """The plan screen, from the setup's Plan; the setup's worker waits on it, so it is polled
    for, not settled."""
    await pilot.press("ctrl+r")
    return await arrived(pilot, PlanScreen, seconds)


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
