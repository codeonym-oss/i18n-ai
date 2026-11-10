"""Home: the tree at a glance, from its scan and its fallback record. The figures are counted by
hand from examples/i18next: the source (en) has 15 messages in common.json and 9 in
auth/login.json; French adds a plural form to each file; fr/common.json keeps 3 of its 16
(title, home, settings: its welcome breaks a placeholder), and fr/auth/login.json is missing."""

from pathlib import Path

import pytest
from textual.widgets import Static

from i18n_ai.cli.tui.home import HomeScreen
from support.fakes import FakeGateway
from support.tui import fallen, settle, tui


def figures(screen: HomeScreen) -> dict[str, tuple[str, str]]:
    """Each card's label: its figure and its note."""
    shown: dict[str, tuple[str, str]] = {}
    for tile in screen.query(".kpi"):
        label, value, note = (str(static.content) for static in tile.query(Static))
        shown[label] = (value, note)
    return shown


def heatmap(screen: HomeScreen) -> list[list[str]]:
    """The heatmap's rows, its header first."""
    grid = screen.query_one("#heatmap")
    cells = [str(static.content) for static in grid.query(Static)]
    width = int(grid.styles.grid_size_columns)
    return [cells[i : i + width] for i in range(0, len(cells), width)]


async def test_home_shows_the_trees_figures_and_its_heatmap(isolated: Path) -> None:
    app = tui(isolated)
    async with app.run_test(size=(160, 45)) as pilot:
        await settle(pilot)
        home = app.screen
        assert isinstance(home, HomeScreen)

        assert figures(home) == {
            "COVERAGE": ("11%", "translated, all locales"),
            "MESSAGES": ("24", "in the source, 2 files"),
            "FALLBACKS": ("0", "kept their source text"),
            "LOCALES": ("1", "en → fr"),
        }
        assert heatmap(home) == [
            ["", "auth/login.json", "common.json", "TOTAL"],
            ["fr French", "—", "18%", "3/26"],
        ]
        assert not home.query_one("#banner").display
        assert app.fallbacks == 0


async def test_a_recorded_fallback_shows_in_its_cell_and_the_banner(
    isolated: Path, gateway: FakeGateway
) -> None:
    await fallen(isolated, gateway, "app.welcome")
    app = tui(isolated)
    async with app.run_test(size=(160, 45)) as pilot:
        await settle(pilot)
        home = app.screen
        assert isinstance(home, HomeScreen)

        assert figures(home)["FALLBACKS"] == ("1", "kept their source text")
        assert home.query_one(".kpi-value.-warning")
        row = heatmap(home)[1]
        assert "◐" not in row[1]
        assert row[2].endswith("◐ 1")
        banner = home.query_one("#banner-text", Static)
        assert home.query_one("#banner").display
        assert str(banner.content) == "1 fallback kept its source text"
        assert app.fallbacks == 1

        await pilot.press("v")
        await settle(pilot)
        assert app.current_mode == "review"


@pytest.mark.parametrize("size", [(160, 45), (80, 24)])
async def test_with_no_tree_home_says_how_to_set_one_up(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, size: tuple[int, int]
) -> None:
    project = tmp_path / "empty"
    project.mkdir()
    monkeypatch.chdir(project)
    app = tui(project)
    async with app.run_test(size=size) as pilot:
        await settle(pilot)
        home = app.screen
        assert isinstance(home, HomeScreen)

        empty = home.query_one("#home-empty", Static)
        assert empty.display
        assert str(empty.content) == "No locale tree found here · ctrl+n to set one up"
        assert not home.query_one("#home").display


async def test_accepting_in_review_clears_the_sidebars_count(
    isolated: Path, gateway: FakeGateway
) -> None:
    await fallen(isolated, gateway, "app.welcome")
    app = tui(isolated)
    async with app.run_test(size=(160, 45)) as pilot:
        await settle(pilot)
        assert app.fallbacks == 1
        await pilot.press("v")
        await settle(pilot)

        await pilot.press("a")
        await settle(pilot)

        assert app.fallbacks == 0
