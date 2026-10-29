"""The TUI, driven with Textual's pilot in a copy of the examples, with the fake model."""

import asyncio
import json
import time
from pathlib import Path

import pytest
from textual.coordinate import Coordinate
from textual.pilot import Pilot
from textual.widgets import DataTable, Input, Log, Select, SelectionList, Static
from textual.widgets.select import InvalidSelectValueError

from i18n_ai.application.exports.locale import ScanReport, SourceFileView, TargetView
from i18n_ai.cli.tui import I18nAiApp
from i18n_ai.cli.tui.confirm import ConfirmScreen
from i18n_ai.cli.tui.grid import JobGrid
from i18n_ai.cli.tui.plan import PlanScreen
from i18n_ai.cli.tui.run import RunScreen
from i18n_ai.cli.tui.setup import SetupScreen
from i18n_ai.di import bootstrap
from i18n_ai.runtime.config import GenerationConfig
from i18n_ai.runtime.settings import Settings
from support.fakes import FakeGateway, FakeModel, InstalledCatalog

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


async def ready(pilot: Pilot[None], *targets: str) -> None:
    """The form filled in, with `targets` checked as well."""
    screen = pilot.app.screen
    for target in targets:
        screen.query_one("#targets", SelectionList).select(target)
    await pick(pilot, "#provider", "openai")
    screen.query_one("#key", Input).value = "sk-test"
    await pick(pilot, "#model", "fake-model")


def cells(screen: PlanScreen | RunScreen) -> list[list[str]]:
    """The grid, its header first."""
    grid = screen.query_one(DataTable)
    header = [str(column.label) for column in grid.columns.values()]
    return [header] + [[str(cell) for cell in grid.get_row_at(i)] for i in range(grid.row_count)]


def total(screen: PlanScreen) -> str:
    return str(screen.query_one("#total", Static).content)


async def on_cell(pilot: Pilot[None], screen: PlanScreen, row: int, column: int, key: str) -> None:
    screen.query_one(DataTable).cursor_coordinate = Coordinate(row, column)
    await pilot.press(key)
    await pilot.pause()


def text(screen: RunScreen) -> str:
    return str(screen.query_one("#receipt", Static).content)


async def test_the_form_starts_from_the_projects_preset(isolated: Path) -> None:
    app = tui(isolated)
    async with app.run_test(size=(100, 40)) as pilot:
        await settle(pilot)
        screen = app.screen

        assert isinstance(screen, SetupScreen)
        assert app.sub_title == "i18next preset"
        assert screen.query_one("#tree", Select).value == "locales"
        targets = screen.query_one("#targets", SelectionList)
        assert targets.selected == ["fr"]
        assert str(targets.get_option_at_index(0).prompt) == "fr — French · in the tree"
        assert not screen.query_one("#source-row").display
        assert str(screen.query_one("#plan", Static).content) == "2 files · 1 locale"


async def test_the_model_waits_for_its_provider_and_a_missing_key_is_asked(
    isolated: Path,
) -> None:
    app = tui(isolated)
    async with app.run_test(size=(100, 40)) as pilot:
        await settle(pilot)
        screen = app.screen
        assert screen.query_one("#model", Select).disabled

        await pick(pilot, "#provider", "openai")

        assert not screen.query_one("#model", Select).disabled
        assert screen.query_one("#model", Select).is_blank()
        assert screen.query_one("#key", Input).display
        assert screen.query_one("#key", Input).password


async def test_the_search_keeps_what_is_checked(isolated: Path) -> None:
    app = tui(isolated)
    async with app.run_test(size=(100, 40)) as pilot:
        await settle(pilot)
        screen = app.screen
        await pilot.click("#search")
        await pilot.press(*"germ")
        await settle(pilot)
        targets = screen.query_one("#targets", SelectionList)
        listed = [str(targets.get_option_at_index(i).prompt) for i in range(targets.option_count)]
        assert listed[0] == "de — German"
        assert all("German" in title for title in listed)
        targets.select("de")
        await settle(pilot)

        screen.query_one("#search", Input).value = ""
        await settle(pilot)

        assert sorted(targets.selected) == ["de", "fr"]
        assert str(screen.query_one("#plan", Static).content) == "2 files · 2 locales"


async def test_a_run_writes_the_targets_and_says_how_to_run_it_again(
    isolated: Path, vault: object
) -> None:
    app = tui(isolated)
    async with app.run_test(size=(120, 40)) as pilot:
        await settle(pilot)
        screen = app.screen
        await pick(pilot, "#provider", "openai")
        screen.query_one("#key", Input).value = "sk-test"
        await pick(pilot, "#model", "fake-model")

        await planning(pilot)
        await pilot.press("ctrl+r")
        run = await ended(pilot)

        receipt = text(run)
        assert "Generated with openai:fake-model" in receipt
        assert "To run it again: i18n-ai generate locales -t fr -m openai:fake-model" in receipt
        french = json.loads((isolated / "locales/fr/common.json").read_text(encoding="utf-8"))
        assert french["app"]["welcome"]  # the fake's, or the good one kept
        assert cells(run)[1:] == [
            ["auth/login.json", "written"],
            ["common.json", "written"],
        ]

        await pilot.press("b")
        await settle(pilot)
        assert isinstance(app.screen, SetupScreen)


async def test_the_source_is_asked_when_the_tree_cannot_tell(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    for locale in ("fr", "de"):
        (tmp_path / "site/locales" / locale).mkdir(parents=True)
        (tmp_path / "site/locales" / locale / "app.json").write_text('{"hello": "Bonjour"}')
    monkeypatch.chdir(tmp_path / "site")
    app = tui(tmp_path / "site")
    async with app.run_test(size=(100, 40)) as pilot:
        await settle(pilot)
        screen = app.screen
        await pick(pilot, "#tree", "locales")
        assert screen.query_one("#source-row").display
        assert screen.query_one("#targets", SelectionList).disabled

        await pick(pilot, "#source", "fr")

        targets = screen.query_one("#targets", SelectionList)
        assert not targets.disabled
        assert targets.selected == ["de"]


async def test_declining_the_install_goes_back_to_the_form(
    isolated: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(InstalledCatalog, "is_installed", lambda self, module: False)
    app = tui(isolated)
    async with app.run_test(size=(100, 40)) as pilot:
        await settle(pilot)
        await pick(pilot, "#provider", "ollama")
        await pick(pilot, "#model", "ollama-pick")

        await pilot.press("ctrl+r")
        await pilot.pause(0.2)
        assert isinstance(app.screen, ConfirmScreen)
        assert "needs langchain-ollama" in str(app.screen.question)
        await pilot.press("n")
        await settle(pilot)

        assert isinstance(app.screen, SetupScreen)
        assert not (isolated / "locales/de").exists()


async def test_the_settings_model_is_the_default(isolated: Path) -> None:
    app = tui(isolated, model="openai:old-model")
    async with app.run_test(size=(100, 40)) as pilot:
        await settle(pilot)

        assert app.screen.query_one("#provider", Select).value == "openai"
        assert app.screen.query_one("#model", Select).value == "old-model"


async def test_another_provider_clears_the_models(isolated: Path) -> None:
    app = tui(isolated, model="openai:old-model")
    async with app.run_test(size=(100, 40)) as pilot:
        await settle(pilot)

        await pick(pilot, "#provider", "ollama")

        models = app.screen.query_one("#model", Select)
        assert models.is_blank()
        with pytest.raises(InvalidSelectValueError):
            models.value = "old-model"
        models.value = "ollama-pick"


async def test_with_no_tree_found_its_path_is_typed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = tmp_path / "project"
    # out/ is left out of the search
    (project / "out/i18n/en").mkdir(parents=True)
    (project / "out/i18n/en/app.json").write_text('{"hello": "Hello"}')
    monkeypatch.chdir(project)
    app = tui(project)
    async with app.run_test(size=(100, 40)) as pilot:
        await settle(pilot)
        screen = app.screen
        assert not screen.query_one("#tree", Select).display
        path = screen.query_one("#tree-path", Input)
        assert path.display

        path.value = "out/i18n"
        await path.action_submit()
        await settle(pilot)

        assert not screen.query_one("#targets", SelectionList).disabled


async def test_run_waits_for_the_form(isolated: Path) -> None:
    app = tui(isolated)
    async with app.run_test(size=(100, 40)) as pilot:
        await settle(pilot)

        await pilot.press("ctrl+r")
        await settle(pilot)

        assert isinstance(app.screen, SetupScreen)
        assert any("Pick a locale tree" in str(n.message) for n in app._notifications)


async def test_the_palette_quits(isolated: Path) -> None:
    app = tui(isolated)
    async with app.run_test(size=(100, 40)) as pilot:
        await settle(pilot)

        await pilot.press("ctrl+p")
        await pilot.press(*"quit")
        await pilot.pause(0.3)
        await pilot.press("enter")
        await pilot.pause(0.3)

        assert not app.is_running


async def test_every_field_fits_80_columns(isolated: Path) -> None:
    app = tui(isolated)
    async with app.run_test(size=(80, 24)) as pilot:
        await settle(pilot)
        await pick(pilot, "#provider", "openai")
        screen = app.screen

        for selector in ("#tree", "#targets", "#output", "#provider", "#model", "#key", "#next"):
            field = screen.query_one(selector)
            screen.scroll_to_widget(field, animate=False)
            await pilot.pause()
            assert field.region.width > 0, selector
            assert field.region.right <= 80, selector
            assert 0 < field.region.bottom <= 24, selector


async def test_the_plan_shows_each_file_and_locale(isolated: Path, vault: object) -> None:
    app = tui(isolated)
    async with app.run_test(size=(100, 40)) as pilot:
        await settle(pilot)
        await ready(pilot, "de")

        plan = await planning(pilot)

        assert cells(plan) == [
            ["File", "fr", "de"],
            ["auth/login.json", "new 10", "new 9"],
            ["common.json", "fill 13", "new 15"],
        ]
        assert total(plan) == "4 agents · 47 messages"
        assert "Left out: meta.json" in str(plan.query_one("#left-out", Static).content)


async def test_a_cell_a_row_or_a_column_turns_off(isolated: Path, vault: object) -> None:
    app = tui(isolated)
    async with app.run_test(size=(100, 40)) as pilot:
        await settle(pilot)
        await ready(pilot, "de")
        plan = await planning(pilot)

        await on_cell(pilot, plan, 1, 2, "space")
        assert cells(plan)[2] == ["common.json", "fill 13", "off"]
        assert total(plan) == "3 agents · 32 messages"

        await on_cell(pilot, plan, 0, 1, "c")
        assert cells(plan)[1:] == [
            ["auth/login.json", "off", "new 9"],
            ["common.json", "off", "off"],
        ]

        await on_cell(pilot, plan, 1, 0, "r")  # all off already: back on
        assert cells(plan)[2] == ["common.json", "fill 13", "new 15"]
        assert total(plan) == "3 agents · 37 messages"
        await on_cell(pilot, plan, 0, 0, "r")
        assert cells(plan)[1] == ["auth/login.json", "off", "off"]


async def test_the_plan_runs_nothing_with_every_cell_off(isolated: Path, vault: object) -> None:
    app = tui(isolated)
    async with app.run_test(size=(100, 40)) as pilot:
        await settle(pilot)
        await ready(pilot)
        plan = await planning(pilot)

        await on_cell(pilot, plan, 0, 1, "c")
        await pilot.press("ctrl+r")
        await pilot.pause()

        assert app.screen is plan
        assert any("Every cell is off" in str(n.message) for n in app._notifications)

        await pilot.press("b")
        await settle(pilot)
        assert isinstance(app.screen, SetupScreen)


async def test_a_cell_turned_off_is_not_written(isolated: Path, vault: object) -> None:
    app = tui(isolated)
    async with app.run_test(size=(120, 40)) as pilot:
        await settle(pilot)
        await ready(pilot, "de")
        plan = await planning(pilot)

        await on_cell(pilot, plan, 1, 2, "space")
        await pilot.press("ctrl+r")
        run = await ended(pilot)

        assert (isolated / "locales/de/auth/login.json").is_file()
        assert not (isolated / "locales/de/common.json").exists()
        receipt = text(run)
        assert "To run it again: i18n-ai generate locales -t fr,de -m openai:fake-model" in receipt
        assert "1 single cell was off; this command runs it too." in receipt


async def test_a_row_off_is_excluded_in_the_command(isolated: Path, vault: object) -> None:
    app = tui(isolated)
    async with app.run_test(size=(140, 40)) as pilot:
        await settle(pilot)
        await ready(pilot)
        plan = await planning(pilot)

        await on_cell(pilot, plan, 1, 0, "r")
        await pilot.press("ctrl+r")
        run = await ended(pilot)

        receipt = text(run)
        assert "-m openai:fake-model --exclude common.json" in receipt
        assert "single cell" not in receipt
        assert cells(run)[1:] == [
            ["auth/login.json", "written"],
            ["common.json", "off"],
        ]


async def test_the_plan_fits_80_columns(isolated: Path, vault: object) -> None:
    app = tui(isolated)
    async with app.run_test(size=(80, 24)) as pilot:
        await settle(pilot)
        await ready(pilot, "de", "es", "it", "ja")
        plan = await planning(pilot)

        for selector in ("#grid", "#total", "Footer"):
            field = plan.query_one(selector)
            assert field.region.width > 0, selector
            assert field.region.right <= 80, selector
            assert 0 < field.region.bottom <= 24, selector


async def test_a_plan_with_no_file_takes_its_keys(isolated: Path) -> None:
    report = ScanReport(
        root=isolated,
        layout="directory",
        format="json",
        source="en",
        source_name="English",
        source_path=isolated,
        output=isolated,
        existing=("en",),
        files=(SourceFileView("meta.json", isolated, False, "it looks like data", 0),),
        targets=(TargetView("fr", "French", "ltr", True, ()),),
    )
    app = tui(isolated)
    async with app.run_test(size=(100, 40)) as pilot:
        await settle(pilot)
        plan = PlanScreen(report)
        await app.push_screen(plan)
        await pilot.pause()

        for key in ("space", "r", "c", "ctrl+r"):
            await pilot.press(key)
            await pilot.pause()

        assert app.screen is plan
        assert total(plan) == "0 agents · 0 messages"


async def test_a_retry_shows_in_its_cell_as_it_happens(
    isolated: Path, vault: object, gateway: FakeGateway, monkeypatch: pytest.MonkeyPatch
) -> None:
    gateway.broken_first = {"app.welcome"}
    shown: list[tuple[str, str, str]] = []
    show = JobGrid.show
    monkeypatch.setattr(
        JobGrid,
        "show",
        lambda grid, file, locale, text: (
            shown.append((file, locale, text)),
            show(grid, file, locale, text),
        ),
    )
    app = tui(isolated)
    async with app.run_test(size=(120, 40)) as pilot:
        await settle(pilot)
        await ready(pilot)
        await planning(pilot)
        await pilot.press("ctrl+r")
        await ended(pilot)

    common = [text for file, locale, text in shown if (file, locale) == ("common.json", "fr")]
    assert common == ["translating", "retry 2/3", "written"]


async def test_a_partial_file_is_listed_under_problems(
    isolated: Path, vault: object, gateway: FakeGateway
) -> None:
    gateway.broken_first = {"app.welcome"}
    app = tui(isolated, attempts=1)
    async with app.run_test(size=(120, 40)) as pilot:
        await settle(pilot)
        await ready(pilot)
        await planning(pilot)
        await pilot.press("ctrl+r")
        run = await ended(pilot)

        assert cells(run)[2] == ["common.json", "partial"]
        problems = run.query_one("#problems", Log)
        assert list(problems.lines) == ["common.json → fr: 1 fallback"]


async def test_the_run_shows_waiting_cells_and_the_ones_off(isolated: Path, vault: object) -> None:
    app = tui(isolated)
    async with app.run_test(size=(120, 40)) as pilot:
        await settle(pilot)
        await ready(pilot, "de")
        plan = await planning(pilot)
        await on_cell(pilot, plan, 1, 2, "space")

        await pilot.press("ctrl+r")
        run = await ended(pilot)

        assert cells(run)[1:] == [
            ["auth/login.json", "written", "written"],
            ["common.json", "written", "off"],
        ]


async def test_a_run_goes_from_waiting_to_written(
    isolated: Path, vault: object, gateway: FakeGateway, monkeypatch: pytest.MonkeyPatch
) -> None:
    classified, translated = asyncio.Event(), asyncio.Event()
    classify, translate = gateway.classify, gateway.translate

    async def held_classify(file, source):  # type: ignore[no-untyped-def]
        await classified.wait()
        return await classify(file, source)

    async def held_translate(batch):  # type: ignore[no-untyped-def]
        await translated.wait()
        return await translate(batch)

    monkeypatch.setattr(gateway, "classify", held_classify)
    monkeypatch.setattr(gateway, "translate", held_translate)
    app = tui(isolated)
    async with app.run_test(size=(120, 40)) as pilot:
        await settle(pilot)
        await ready(pilot)
        await planning(pilot)
        await pilot.press("ctrl+r")
        run = await showing(pilot, "waiting")
        assert cells(run)[1:] == [["auth/login.json", "waiting"], ["common.json", "waiting"]]

        classified.set()
        await showing(pilot, "translating", every=True)

        translated.set()
        await ended(pilot)
        assert cells(run)[1:] == [["auth/login.json", "written"], ["common.json", "written"]]


async def showing(pilot: Pilot[None], text: str, every: bool = False) -> RunScreen:
    """The run screen, once one of its cells (or `every` one) reads `text`."""
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        screen = pilot.app.screen
        if isinstance(screen, RunScreen) and screen.is_mounted:
            states = [cell for row in cells(screen)[1:] for cell in row[1:]]
            if (all if every else any)(state == text for state in states):
                return screen
        await pilot.pause(0.05)
    raise AssertionError(f"no cell reads {text!r}")
