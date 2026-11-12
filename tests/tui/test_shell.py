"""The shell every screen sits in: its theme, its frame at each size, its sections and their
keys."""

import asyncio
import time
from pathlib import Path

import pytest
from mediary import Mediator
from textual.widgets import ContentSwitcher, OptionList, Select, Static

from i18n_ai.application.exports.locale import ScanLocaleTreeQuery
from i18n_ai.cli.tui.home import HomeScreen
from i18n_ai.cli.tui.kit.shell import ShellScreen
from i18n_ai.cli.tui.plan import PlanScreen
from i18n_ai.cli.tui.review import ReviewScreen
from i18n_ai.cli.tui.run import RunScreen
from i18n_ai.cli.tui.setup import SetupScreen
from i18n_ai.runtime.answers import Answers, save_answers
from support.fakes import FakeGateway
from support.tui import ended, planning, ready, settle, tui


async def test_the_app_is_aurora_and_offers_no_other_theme(isolated: Path) -> None:
    app = tui(isolated)
    async with app.run_test(size=(160, 45)) as pilot:
        await settle(pilot)

        assert app.theme == "aurora"
        titles = [command.title for command in app.get_system_commands(app.screen)]
        assert "Theme" not in titles
        assert "Quit" in titles


def sidebar(screen: ShellScreen) -> list[str]:
    entries = screen.query_one("#sidebar", OptionList)
    return [str(entries.get_option_at_index(i).prompt) for i in range(entries.option_count)]


async def test_a_wide_terminal_shows_the_sidebars_labels(isolated: Path) -> None:
    app = tui(isolated)
    async with app.run_test(size=(160, 45)) as pilot:
        await settle(pilot)
        screen = app.screen

        assert isinstance(screen, ShellScreen)
        assert not screen.has_class("-narrow")
        assert [entry.split()[:2] for entry in sidebar(screen)] == [
            ["⌂", "Home"],
            ["▶", "Run"],
            ["◐", "Review"],
        ]
        assert screen.query_one("#body").display
        assert not screen.query_one("#notice").display


async def test_a_narrow_terminal_turns_the_sidebar_into_a_rail(isolated: Path) -> None:
    app = tui(isolated)
    async with app.run_test(size=(100, 30)) as pilot:
        await settle(pilot)
        screen = app.screen

        assert isinstance(screen, ShellScreen)
        assert screen.has_class("-narrow")
        assert sidebar(screen) == ["⌂", "▶", "◐"]
        assert screen.query_one("#sidebar").region.width <= 6


async def test_a_terminal_under_80_by_24_says_it_is_too_small(isolated: Path) -> None:
    app = tui(isolated)
    async with app.run_test(size=(70, 20)) as pilot:
        await settle(pilot)
        screen = app.screen

        assert isinstance(screen, ShellScreen)
        assert not screen.query_one("#body").display
        notice = screen.query_one("#notice", Static)
        assert notice.display
        assert str(notice.content) == "i18n-ai needs 80×24; this terminal is 70×20"


async def test_the_app_opens_on_home_and_its_keys_move_between_sections(isolated: Path) -> None:
    app = tui(isolated)
    async with app.run_test(size=(160, 45)) as pilot:
        await settle(pilot)
        assert isinstance(app.screen, HomeScreen)
        assert str(app.screen.query_one("#status-tree", Static).content) == "locales"

        await pilot.press("ctrl+n")
        await settle(pilot)
        assert isinstance(app.screen, SetupScreen)
        assert app.screen.query_one("#tree", Select).value == "locales"

        await pilot.press("ctrl+o")
        await settle(pilot)
        assert isinstance(app.screen, HomeScreen)


async def test_a_run_goes_on_while_home_shows_and_is_there_on_return(
    isolated: Path, vault: object, gateway: FakeGateway
) -> None:
    gateway.hold = asyncio.Event()
    app = tui(isolated)
    async with app.run_test(size=(160, 45)) as pilot:
        await settle(pilot)
        await pilot.press("ctrl+n")
        await settle(pilot)
        await ready(pilot)
        await planning(pilot)
        await pilot.press("ctrl+r")
        await pilot.pause(0.3)
        run = app.screen
        assert isinstance(run, RunScreen)
        assert not run.done

        await pilot.press("ctrl+o")
        await pilot.pause()
        assert isinstance(app.screen, HomeScreen)
        gateway.hold.set()
        deadline = time.monotonic() + 10
        while not run.done and time.monotonic() < deadline:
            await pilot.pause(0.05)
        assert isinstance(app.screen, HomeScreen)

        await pilot.press("ctrl+n")
        await pilot.pause()
        assert app.screen is run
        lines = run.query_one("#feed").query(".event").results(Static)
        assert any("Generated with openai:fake-model" in str(line.content) for line in lines)


async def test_a_plan_shows_in_run_when_another_section_was_picked_meanwhile(
    isolated: Path, vault: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    scanned = asyncio.Event()
    send = Mediator.send

    async def held(mediator, request):  # type: ignore[no-untyped-def]
        if isinstance(request, ScanLocaleTreeQuery) and request.targets and gate:
            await scanned.wait()
        return await send(mediator, request)

    gate = False
    monkeypatch.setattr(Mediator, "send", held)
    app = tui(isolated)
    async with app.run_test(size=(160, 45)) as pilot:
        await settle(pilot)
        await pilot.press("ctrl+n")
        await settle(pilot)
        await ready(pilot)
        gate = True

        await pilot.press("ctrl+r")
        await pilot.pause()
        await pilot.press("ctrl+o")
        await pilot.pause()
        assert isinstance(app.screen, HomeScreen)
        scanned.set()
        await pilot.pause(0.3)

        assert app.current_mode == "run"
        assert isinstance(app.screen, PlanScreen)


async def test_a_runs_review_retries_with_its_model_and_b_goes_back_to_the_run(
    isolated: Path, vault: object, gateway: FakeGateway
) -> None:
    gateway.broken_first = {"app.welcome"}
    app = tui(isolated, attempts=1)
    async with app.run_test(size=(160, 45)) as pilot:
        await settle(pilot)
        await pilot.press("ctrl+n")
        await settle(pilot)
        await ready(pilot)
        await planning(pilot)
        await pilot.press("ctrl+r")
        run = await ended(pilot)

        await pilot.press("v")
        await settle(pilot)
        review = app.screen
        assert isinstance(review, ReviewScreen)
        assert app.current_mode == "review"
        assert review.check_action("retry", ()) is True

        await pilot.press("b")
        await settle(pilot)
        assert app.screen is run


async def test_review_from_home_is_on_homes_tree_with_the_last_model(isolated: Path) -> None:
    save_answers(isolated, Answers(tree="locales", model="openai:fake-model"))
    app = tui(isolated)
    async with app.run_test(size=(160, 45)) as pilot:
        await settle(pilot)

        await pilot.press("v")
        await settle(pilot)

        review = app.screen
        assert isinstance(review, ReviewScreen)
        assert str(review.query_one("#status-tree", Static).content) == "locales"
        assert not review.query_one("#hint").display  # a model: retry is on
        await pilot.press("b")
        await settle(pilot)
        assert isinstance(app.screen, HomeScreen)


async def test_the_switcher_moves_home_and_the_setup_but_not_a_run_going(
    examples: Path, vault: object, gateway: FakeGateway, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(examples)
    app = tui(examples)
    async with app.run_test(size=(160, 45)) as pilot:
        await settle(pilot)
        home = app.screen
        assert isinstance(home, HomeScreen)
        switcher = home.query_one("#switcher", Select)
        assert switcher.display
        assert switcher.value == "bundle/i18n.json"
        assert str(home.query(".kpi").last().query(Static).last().content) == "en → es"

        switcher.value = "i18next/locales"
        await settle(pilot)

        assert app.locale_tree == "i18next/locales"
        assert str(home.query(".kpi").last().query(Static).last().content) == "en → fr"
        await pilot.press("ctrl+n")
        await settle(pilot)
        setup = app.screen
        assert isinstance(setup, SetupScreen)
        assert setup.query_one("#tree", Select).value == "i18next/locales"
        assert setup.query_one("#switcher", Select).value == "i18next/locales"
        # Another tree from the command bar keeps the wizard on its step
        await pilot.click("#step-model")
        setup.query_one("#switcher", Select).value = "bundle/i18n.json"
        await settle(pilot)
        assert setup.query_one("#tree", Select).value == "bundle/i18n.json"
        assert setup.query_one("#wizard", ContentSwitcher).current == "model-step"
        setup.query_one("#switcher", Select).value = "i18next/locales"
        await settle(pilot)

        gateway.hold = asyncio.Event()
        await ready(pilot)
        await planning(pilot)
        await pilot.press("ctrl+r")
        await pilot.pause(0.3)
        run = app.screen
        assert isinstance(run, RunScreen)
        run.query_one("#switcher", Select).value = "bundle/i18n.json"
        await pilot.pause()

        assert app.screen is run
        assert str(run.query_one("#status-tree", Static).content).endswith("  ·  i18next/locales")
        gateway.hold.set()
        await ended(pilot)


async def test_one_tree_needs_no_switcher(isolated: Path) -> None:
    app = tui(isolated)
    async with app.run_test(size=(160, 45)) as pilot:
        await settle(pilot)

        assert not app.screen.query_one("#switcher", Select).display
