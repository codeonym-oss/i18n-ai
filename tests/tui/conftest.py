from collections.abc import Awaitable, Callable
from pathlib import Path

import pytest
from syrupy.assertion import SnapshotAssertion
from syrupy.extensions.single_file import SingleFileSnapshotExtension, WriteMode
from textual.pilot import Pilot

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
                await setup(pilot)
                await settle(pilot)
            svg = app.export_screenshot(title="i18n-ai")
        assert svg == snapshot.use_extension(SvgSnapshot)

    return check
