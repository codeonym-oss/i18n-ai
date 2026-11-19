"""The palette: the commands, the tree's locales and its files, by group; a prefix keeps one
group, and choosing a result does what it says."""

import json
from pathlib import Path

from textual.app import App, ComposeResult
from textual.pilot import Pilot
from textual.widgets import Input, OptionList, Static

from i18n_ai.cli.tui.home import HomeScreen
from i18n_ai.cli.tui.kit.palette import PaletteEntry, PaletteScreen
from i18n_ai.cli.tui.kit.widgets import LocaleCard
from i18n_ai.cli.tui.setup import SetupScreen
from support.tui import settle, tui

ENTRIES = [
    PaletteEntry("Commands", "▶", "Run", "Set up a new run", "ctrl+n", lambda: None),
    PaletteEntry("Commands", "✕", "Quit", "Leave i18n-ai", "q", lambda: None),
    PaletteEntry("Go to", "◍", "fr", "French", "", lambda: None),
    PaletteEntry("Files", "▤", "common.json", "6 messages", "", lambda: None),
]


def titles(screen: PaletteScreen) -> list[str]:
    found = screen.query_one("#palette-results", OptionList)
    return [
        str(found.get_option_at_index(i).prompt).split("  ")[0][2:].strip()
        if not found.get_option_at_index(i).disabled
        else str(found.get_option_at_index(i).prompt)
        for i in range(found.option_count)
    ]


class Host(App[None]):
    def __init__(self) -> None:
        super().__init__()
        self.chosen: list[PaletteEntry | None] = []

    def compose(self) -> ComposeResult:
        yield Static("")

    def on_mount(self) -> None:
        self.push_screen(PaletteScreen(ENTRIES), self.chosen.append)


async def typed(pilot: Pilot[None], text: str) -> PaletteScreen:
    screen = pilot.app.screen
    assert isinstance(screen, PaletteScreen)
    screen.query_one(Input).value = text
    await pilot.pause()
    return screen


async def test_no_prefix_searches_every_group() -> None:
    async with Host().run_test() as pilot:
        screen = await typed(pilot, "")

        assert titles(screen) == ["COMMANDS", "Run", "Quit", "GO TO", "fr", "FILES", "common.json"]


async def test_each_prefix_keeps_its_group() -> None:
    async with Host().run_test() as pilot:
        assert titles(await typed(pilot, ">")) == ["COMMANDS", "Run", "Quit"]
        assert titles(await typed(pilot, "@")) == ["GO TO", "fr"]
        assert titles(await typed(pilot, "#")) == ["FILES", "common.json"]
        assert titles(await typed(pilot, ">qu")) == ["COMMANDS", "Quit"]


async def test_a_search_narrows_and_nothing_matching_says_so() -> None:
    async with Host().run_test() as pilot:
        assert titles(await typed(pilot, "com")) == ["FILES", "common.json"]
        assert titles(await typed(pilot, "zzz")) == ["nothing matches"]


async def test_enter_chooses_the_highlighted_entry_and_escape_none() -> None:
    host = Host()
    async with host.run_test() as pilot:
        await typed(pilot, ">")
        await pilot.press("down", "enter")
        await pilot.pause()
        assert [entry.title if entry else None for entry in host.chosen] == ["Quit"]

        host.push_screen(PaletteScreen(ENTRIES), host.chosen.append)
        await pilot.pause()
        await pilot.press("escape")
        await pilot.pause()
        assert host.chosen[-1] is None


async def palette(pilot: Pilot[None], text: str) -> PaletteScreen:
    await settle(pilot)
    await pilot.press("ctrl+p")
    await settle(pilot)
    return await typed(pilot, text)


async def test_the_palette_offers_the_apps_commands_the_trees_locales_and_files(
    isolated: Path,
) -> None:
    app = tui(isolated)
    async with app.run_test(size=(160, 45)) as pilot:
        screen = await palette(pilot, "")

        assert titles(screen) == [
            "COMMANDS",
            "Home",
            "Run",
            "Review",
            "Quit",
            "GO TO",
            "fr",
            "FILES",
            "auth/login.json",
            "common.json",
        ]


async def test_a_command_does_what_its_key_does(isolated: Path) -> None:
    app = tui(isolated)
    async with app.run_test(size=(160, 45)) as pilot:
        await palette(pilot, ">run")
        await pilot.press("enter")
        await settle(pilot)

        assert isinstance(app.screen, SetupScreen)


async def test_a_locale_opens_a_run_into_it(isolated: Path) -> None:
    german = isolated / "locales/de/common.json"
    german.parent.mkdir()
    german.write_text(json.dumps({"app": {"title": "Acme"}}), encoding="utf-8")
    app = tui(isolated)
    async with app.run_test(size=(160, 45)) as pilot:
        await palette(pilot, "@de")
        await pilot.press("enter")
        await settle(pilot)

        screen = app.screen
        assert isinstance(screen, SetupScreen)
        assert screen.step == "targets"
        assert "de" in [card.code for card in screen.query(LocaleCard) if card.picked]


async def test_a_file_lights_its_coverage_on_home(isolated: Path) -> None:
    app = tui(isolated)
    async with app.run_test(size=(160, 45)) as pilot:
        await pilot.press("ctrl+n")
        await palette(pilot, "#login")
        await pilot.press("enter")
        await settle(pilot)

        screen = app.screen
        assert isinstance(screen, HomeScreen)
        lit = [str(head.render()) for head in screen.query(".heat-head.-lit")]
        assert lit == ["auth/login.json"]
