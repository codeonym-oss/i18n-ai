import time
from collections.abc import Awaitable, Callable
from pathlib import Path

import pytest
from syrupy.assertion import SnapshotAssertion
from syrupy.extensions.single_file import SingleFileSnapshotExtension, WriteMode
from textual.pilot import Pilot
from textual.widgets import Footer

from i18n_ai.cli.tui import I18nAiApp
from i18n_ai.di import bootstrap
from support.fakes import FakeGateway, FakeModel
from support.tui import Snap, settle

KEYS = ("OPENAI_API_KEY", "ANTHROPIC_API_KEY")


@pytest.fixture
def gateway() -> FakeGateway:
    return FakeGateway()


@pytest.fixture(autouse=True)
def isolated(monkeypatch: pytest.MonkeyPatch, examples: Path, gateway: FakeGateway) -> Path:
    """In the i18next example, with no provider key from the developer's machine, and the fake
    model before the overrides, so that the TUI's progress wins over the fake's."""
    project = examples / "i18next"
    monkeypatch.chdir(project)
    for key in KEYS:
        monkeypatch.setenv(key, "")
        monkeypatch.delenv(key)
    build = bootstrap.build_container
    monkeypatch.setattr(
        bootstrap,
        "build_container",
        lambda mediator, console, *overrides: build(
            mediator, console, FakeModel(gateway), *overrides
        ),
    )
    return project


class SvgSnapshot(SingleFileSnapshotExtension):
    """A screen as Textual's SVG export, one file per snapshot."""

    file_extension = "svg"
    _write_mode = WriteMode.TEXT


@pytest.fixture
def snap(snapshot: SnapshotAssertion) -> Snap:
    """`app` at `size`, after `setup(pilot)` when given, matches its SVG under `__snapshots__/`;
    `--snapshot-update` writes it."""

    async def check(
        app: I18nAiApp,
        size: tuple[int, int],
        setup: Callable[[Pilot[None]], Awaitable[None]] | None = None,
    ) -> None:
        async with app.run_test(size=size) as pilot:
            await settle(pilot)
            if setup is not None:
                # Not `settle`: a screen pushed from a worker (the plan) holds that worker until
                # it closes, so waiting for every worker would never end; each step settles itself
                await setup(pilot)
                await pilot.pause()
            await footed(pilot)
            svg = app.export_screenshot(title="i18n-ai")
        assert svg == snapshot.use_extension(SvgSnapshot)

    return check


async def footed(pilot: Pilot[None], seconds: float = 5) -> None:
    """Until the footer shows its keys: it recomposes after a refresh, removing them first, and
    a slow machine can take the screenshot in between."""
    footer = pilot.app.screen.query_one(Footer)
    deadline = time.monotonic() + seconds
    while not footer.children and time.monotonic() < deadline:
        await pilot.pause(0.05)
    await pilot.pause()
